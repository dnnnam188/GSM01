"""Đo hội thoại nhiều lượt và tính trung thực với nguồn (T-012).

Hai lỗ hổng của bộ đo cũ mà file này lấp:

1. **Chỉ đo câu hỏi đơn lẻ.** Golden set 81 câu không có lượt nối tiếp nào, nên
   không bắt được lỗi ngày 2026-08-26: hỏi tiếp *"thế còn xe máy thì sao?"* và
   agent trả lời sai số liệu.
2. **Chỉ đo truy hồi, không đo câu trả lời.** `recall@3 = 100%` chỉ nói "đã lấy
   đúng file", không nói "đã trả lời đúng". Agent hoàn toàn có thể nhận đúng
   đoạn tri thức rồi vẫn đọc nhầm con số trong đó.

`faithfulness` ở đây định nghĩa hẹp và kiểm chứng được: **mọi con số tiền xuất
hiện trong câu trả lời đều phải có mặt trong đoạn tri thức đã truy hồi hoặc
trong kết quả tool.** Con số nào không truy ngược được về nguồn thì coi là bịa.
"""
from __future__ import annotations

import re
import time
import uuid
from typing import Any

from eval.datasets.multiturn import MULTITURN_CASES
from src.backend.agent.graph import ANSWER_SYSTEM, run_graph
from src.backend.db.connection import get_connection
from src.backend.db.repository import get_user_by_email
from src.backend.llm.client import LLMClient, LLMError

# Con số tiền: từ 4 chữ số trở lên, có hoặc không có dấu phân cách nghìn.
# Ngưỡng 4 chữ số để bỏ qua "2 phút", "3 km", "05 phút" — không phải tiền.
MONEY_RE = re.compile(r"\b\d{1,3}(?:[.,]\d{3})+\b|\b\d{4,}\b")


def _normalise_number(text: str) -> str:
    return re.sub(r"[.,\s]", "", text)


def _create_conversation(customer_id: str) -> str:
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO conversations (customer_id, thread_id) VALUES (%s, %s) RETURNING id",
            (customer_id, f"mt-{uuid.uuid4().hex[:10]}"))
        return str(cur.fetchone()[0])


def _drop_conversation(conversation_id: str) -> None:
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM tool_calls WHERE conversation_id = %s", (conversation_id,))
        cur.execute("DELETE FROM messages WHERE conversation_id = %s", (conversation_id,))
        cur.execute("DELETE FROM conversations WHERE id = %s", (conversation_id,))


# Hệ số cho phép khi agent tự tính. Ví dụ hợp lệ: phí chờ 60.000đ/giờ, khách hỏi
# nửa tiếng, agent trả lời 30.000đ — đó là phép tính đúng, không phải bịa.
_DERIVE_FACTORS = (0.25, 1 / 3, 0.5, 2, 3, 4, 1 / 60, 60)


def _source_numbers(evidence: str) -> set[int]:
    values = set()
    for raw in MONEY_RE.findall(evidence):
        digits = _normalise_number(raw)
        if len(digits) >= 3:
            values.add(int(digits))
    return values


def _is_derivable(value: int, sources: set[int]) -> bool:
    """Con số có suy ra được từ nguồn bằng một phép tính đơn giản không?

    Cố ý hẹp: nhân/chia với vài hệ số quen thuộc, hoặc cộng hai con số trong
    nguồn. Không phải để chứng minh agent tính đúng — chỉ để phân biệt
    **suy ra** với **bịa**, vì gắn cờ phép tính đúng là bịa sẽ đẩy ta đi sửa
    agent theo hướng tệ hơn: dạy nó từ chối làm toán.
    """
    if value in sources:
        return True
    for base in sources:
        for factor in _DERIVE_FACTORS:
            candidate = base * factor
            if abs(candidate - value) < 1:
                return True
    for a in sources:
        for b in sources:
            if a + b == value:
                return True
    return False


def _ungrounded_amounts(answer: str, evidence: str) -> list[str]:
    """Con số tiền trong câu trả lời mà KHÔNG truy ngược được về nguồn.

    Đây là định nghĩa hẹp của "bịa": không có trong nguồn, và cũng không suy ra
    được từ nguồn bằng phép tính đơn giản.
    """
    sources = _source_numbers(evidence)
    missing = []
    for raw in MONEY_RE.findall(answer):
        digits = _normalise_number(raw)
        if len(digits) < 4:
            continue
        if not _is_derivable(int(digits), sources):
            missing.append(raw)
    return sorted(set(missing))


async def run_multiturn(limit: int | None = None, delay: float = 0.3) -> dict[str, Any]:
    cases = MULTITURN_CASES[:limit]
    client = LLMClient()
    customer_id = get_user_by_email("demo.customer@gsm.vn")["id"]

    passed_answer = 0
    passed_source = 0
    passed_faithful = 0
    failures: list[dict[str, Any]] = []

    for case in cases:
        conversation_id = _create_conversation(customer_id)
        history: list[dict[str, str]] = []
        answer = ""
        chunks: list[Any] = []
        tool_results: list[Any] = []

        try:
            for turn_text in case["turns"]:
                state = await run_graph(customer_id, conversation_id, turn_text, history)
                chunks = state.get("chunks") or []
                tool_results = state.get("tool_results") or []
                prompt = state.get("answer_prompt")
                if not prompt:
                    answer = state.get("clarify_question", "")
                else:
                    answer = client.generate(prompt, system=ANSWER_SYSTEM, max_tokens=600).text
                history.append({"role": "user", "content": turn_text})
                history.append({"role": "assistant", "content": answer})
                time.sleep(delay)
        except LLMError as exc:
            failures.append({"id": case["id"], "reason": f"LỖI GỌI MODEL: {exc}"})
            _drop_conversation(conversation_id)
            continue

        sources = [c.source_file for c in chunks]
        evidence = "\n".join(c.content for c in chunks) + "\n" + str(tool_results)

        # 1. Câu trả lời có đúng số liệu không
        expects = case["expect"]
        if case.get("expect_any"):
            answer_ok = any(token in answer for token in expects)
        else:
            answer_ok = all(token in answer for token in expects)
        forbidden_hit = [token for token in case["forbid"] if token in answer]
        answer_ok = answer_ok and not forbidden_hit

        # 2. Truy hồi đúng nguồn ở lượt cuối
        source_ok = case["expect_source"] in sources

        # 3. Trung thực: mọi con số tiền phải truy ngược được về nguồn
        ungrounded = _ungrounded_amounts(answer, evidence)
        faithful_ok = not ungrounded

        passed_answer += int(answer_ok)
        passed_source += int(source_ok)
        passed_faithful += int(faithful_ok)

        if not (answer_ok and source_ok and faithful_ok):
            failures.append({
                "id": case["id"], "note": case["note"],
                "turns": case["turns"],
                "answer_ok": answer_ok, "source_ok": source_ok, "faithful_ok": faithful_ok,
                "forbidden_hit": forbidden_hit,
                "ungrounded": ungrounded,
                "sources": sources,
                "answer": answer[:220].replace("\n", " "),
            })
        _drop_conversation(conversation_id)

    total = len(cases)
    return {
        "total": total,
        "answer_correct": passed_answer,
        "source_correct": passed_source,
        "faithful": passed_faithful,
        "failures": failures,
    }
