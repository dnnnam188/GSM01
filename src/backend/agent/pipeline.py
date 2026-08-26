"""Một lượt hội thoại: chạy LangGraph rồi stream câu trả lời ra WebSocket.

Phân chia trách nhiệm:
- `graph.py` lo phần *quyết định*: phân loại, truy hồi, gọi tool, dựng prompt.
- File này lo phần *truyền tải*: stream token, đo TTFT, ghi vết, xuống cấp êm khi hỏng.

Ranh giới này là cố ý. WebSocket cần từng token một để đạt ngưỡng TTFT, còn
LangGraph làm việc theo đơn vị node. Đặt bước sinh câu trả lời ra ngoài graph giữ
cho việc stream đơn giản, đồng thời không cản điểm dừng HITL của T-011 — điểm đó
nằm ở `tool_node`, tức là trước bước này.
"""
from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncIterator
from typing import Any

from src.backend.agent.graph import ANSWER_SYSTEM, run_graph
from src.backend.db import repository as repo
from src.backend.llm.client import LLMClient, LLMError
from src.backend.pii.detector import mask_text

FALLBACK_ANSWER = (
    "Dạ em xin lỗi, hệ thống đang bận nên em chưa tra cứu được ngay lúc này. "
    "Anh/chị vui lòng thử lại sau ít phút, hoặc để em chuyển yêu cầu tới nhân viên hỗ trợ ạ."
)


async def _persist(conversation_id: str, text: str, **kwargs: Any) -> None:
    await asyncio.to_thread(repo.insert_message, conversation_id, "assistant", text, **kwargs)


async def run_turn(customer_id: str, thread_id: str, message: str,
                   client: LLMClient | None = None) -> AsyncIterator[dict[str, Any]]:
    """Chạy một lượt, yield sự kiện cho WebSocket.

    Loại sự kiện: `status`, `intent`, `tool`, `token`, `done`, `error`.
    """
    client = client or LLMClient()
    turn_started = time.perf_counter()

    conversation_id = await asyncio.to_thread(
        repo.get_or_create_conversation, customer_id, thread_id)
    history = await asyncio.to_thread(repo.recent_messages, conversation_id, 6)
    await asyncio.to_thread(repo.insert_message, conversation_id, "user", message)

    yield {"type": "status", "value": "Đang phân tích yêu cầu"}

    # --- Chạy graph -------------------------------------------------------
    try:
        state = await run_graph(customer_id, conversation_id, message, history)
    except LLMError as exc:
        await asyncio.to_thread(
            repo.log_tool_call, conversation_id, "agent_graph", {"message": message},
            status="ERROR", error_type="RETRYABLE", error_message=str(exc)[:500])
        await _persist(conversation_id, FALLBACK_ANSWER)
        yield {"type": "token", "value": FALLBACK_ANSWER}
        yield {"type": "done", "intent": None, "degraded": True}
        return

    intent = state.get("intent")
    yield {"type": "intent", "value": intent,
           "confidence": round(state.get("confidence", 0.0), 2)}

    for call in state.get("tool_results") or []:
        yield {"type": "tool", "name": call["tool"], "ok": call["ok"],
               "replayed": call["replayed"],
               "error": call["error"]["code"] if call.get("error") else None}

    # --- Thiếu thông tin thì hỏi lại, không gọi model sinh câu trả lời -----
    clarify = state.get("clarify_question")
    if clarify:
        await _persist(conversation_id, clarify, intent=intent,
                       intent_confidence=state.get("confidence"),
                       latency_ms=int((time.perf_counter() - turn_started) * 1000))
        yield {"type": "token", "value": clarify}
        yield {"type": "done", "intent": intent, "awaiting_info": True,
               "latency_ms": int((time.perf_counter() - turn_started) * 1000),
               "degraded": False}
        return

    # --- Stream câu trả lời -----------------------------------------------
    yield {"type": "status", "value": "Đang soạn câu trả lời"}
    collected: list[str] = []
    ttft_ms: int | None = None
    usage: dict[str, Any] = {}
    try:
        async for delta, first_ms, meta in client.astream(
                state["answer_prompt"], system=ANSWER_SYSTEM, max_tokens=700):
            if meta:
                usage = meta
                continue
            if first_ms is not None:
                ttft_ms = first_ms
            collected.append(delta)
            yield {"type": "token", "value": delta}
    except LLMError as exc:
        await asyncio.to_thread(
            repo.log_tool_call, conversation_id, "generate_answer",
            {"model": client.answer_model}, status="ERROR", error_type="RETRYABLE",
            error_message=str(exc)[:500])
        if not collected:
            await _persist(conversation_id, FALLBACK_ANSWER, intent=intent,
                           intent_confidence=state.get("confidence"))
            yield {"type": "token", "value": FALLBACK_ANSWER}
            yield {"type": "done", "intent": intent, "degraded": True}
            return

    answer = mask_text("".join(collected))  # lưới an toàn lớp hai (ADR-004)
    await _persist(
        conversation_id, answer, intent=intent,
        intent_confidence=state.get("confidence"),
        model_name=usage.get("model") or client.answer_model,
        provider=usage.get("provider", "gemini"),
        prompt_tokens=usage.get("prompt_tokens"),
        completion_tokens=usage.get("completion_tokens"),
        ttft_ms=ttft_ms, latency_ms=int((time.perf_counter() - turn_started) * 1000))

    pending = state.get("pending_hitl")
    if pending:
        await asyncio.to_thread(repo.set_conversation_status, conversation_id, "WAITING_HUMAN")

    yield {
        "type": "done",
        "intent": intent,
        "ttft_ms": ttft_ms,
        "latency_ms": int((time.perf_counter() - turn_started) * 1000),
        "sources": sorted({c.source_file for c in (state.get("chunks") or [])}),
        "tools_used": [c["tool"] for c in (state.get("tool_results") or [])],
        "prompt_tokens": usage.get("prompt_tokens"),
        "completion_tokens": usage.get("completion_tokens"),
        "provider": usage.get("provider", "gemini"),
        "pending_hitl": pending,
        "degraded": bool(state.get("degraded")),
    }
