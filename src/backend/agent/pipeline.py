"""Vertical slice của agent: một lượt hội thoại đi trọn từ tin nhắn tới câu trả lời.

Đây CHƯA phải LangGraph (việc đó ở T-004). Mục tiêu của T-009 là khai thông toàn
bộ hạ tầng — xác thực, WebSocket, RAG, ghi vết, deploy — trước khi thêm độ phức
tạp của graph. Khi T-004 làm xong, `run_turn` được thay bằng lời gọi graph, còn
phần ghi vết và hợp đồng sự kiện ở đây giữ nguyên.

Nguyên tắc an toàn quan trọng nhất của bản slice: các tool ghi dữ liệu (đặt xe,
huỷ chuyến, hoàn tiền) **chưa được nối**. Agent phải nói rõ là đã ghi nhận và
đang chuyển tiếp, TUYỆT ĐỐI không được nói như thể đã thực hiện xong.
"""
from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncIterator
from typing import Any

from src.backend.agent.router import route
from src.backend.db import repository as repo
from src.backend.llm.client import LLMClient, LLMError
from src.backend.pii.detector import mask_text
from src.backend.rag.retriever import retrieve

# Intent trả lời được trọn vẹn chỉ bằng tri thức chính sách
RAG_INTENTS = {"policy.faq", "fare.inquiry"}
# Intent cần tool ghi dữ liệu — chưa nối ở bản slice này
ACTION_INTENTS = {"booking.create", "booking.cancel", "booking.modify",
                  "refund.request", "complaint.driver", "complaint.lost_item"}

ANSWER_SYSTEM = """Bạn là trợ lý CSKH của hãng gọi xe điện Xanh SM. Trả lời bằng tiếng Việt,
ngắn gọn, lịch sự, xưng "em" và gọi khách là "anh/chị".

QUY TẮC BẮT BUỘC:
- Chỉ dùng thông tin trong phần TRI THỨC CHÍNH SÁCH bên dưới. Không có thì nói thẳng là
  chưa có thông tin và đề nghị chuyển nhân viên hỗ trợ.
- Không bịa số tiền, không bịa mã chuyến, không bịa chính sách.
- Không tiết lộ số điện thoại, địa chỉ đầy đủ hay tên tài xế.
- Nếu khách yêu cầu một hành động (đặt xe, huỷ chuyến, đổi điểm đến, hoàn tiền, tạo khiếu nại):
  nói rằng em ĐÃ GHI NHẬN và đang chuyển tiếp xử lý. TUYỆT ĐỐI KHÔNG nói như thể
  đã thực hiện xong, không xác nhận đã đặt/đã huỷ/đã hoàn tiền.
- Khi trích chính sách, nêu rõ căn cứ (ví dụ: theo biểu phí hiện hành)."""

FALLBACK_ANSWER = (
    "Dạ em xin lỗi, hệ thống đang bận nên em chưa tra cứu được ngay lúc này. "
    "Anh/chị vui lòng thử lại sau ít phút, hoặc để em chuyển yêu cầu tới nhân viên hỗ trợ ạ."
)


def _build_prompt(message: str, chunks: list, history: list[dict[str, Any]]) -> str:
    parts: list[str] = []
    if history:
        lines = [f"{'Khách' if m['role'] == 'user' else 'Trợ lý'}: {m['content']}" for m in history]
        parts.append("LỊCH SỬ HỘI THOẠI GẦN ĐÂY:\n" + "\n".join(lines))
    if chunks:
        body = "\n\n---\n\n".join(f"(Nguồn: {c.source_file})\n{c.content}" for c in chunks)
        parts.append("TRI THỨC CHÍNH SÁCH:\n" + body)
    else:
        parts.append("TRI THỨC CHÍNH SÁCH: (không tìm thấy đoạn nào liên quan)")
    parts.append(f"TIN NHẮN CỦA KHÁCH:\n{message}")
    return "\n\n".join(parts)


async def run_turn(customer_id: str, thread_id: str, message: str,
                   client: LLMClient | None = None) -> AsyncIterator[dict[str, Any]]:
    """Chạy một lượt, yield từng sự kiện cho WebSocket.

    Các loại sự kiện: `status`, `intent`, `token`, `done`, `error`.
    """
    client = client or LLMClient()
    turn_started = time.perf_counter()

    conversation_id = await asyncio.to_thread(repo.get_or_create_conversation, customer_id, thread_id)
    prior = await asyncio.to_thread(repo.recent_messages, conversation_id, 6)
    await asyncio.to_thread(repo.insert_message, conversation_id, "user", message)
    yield {"type": "status", "value": "Đang phân loại yêu cầu"}

    # --- Phân loại ý định -------------------------------------------------
    route_started = time.perf_counter()
    try:
        result = await asyncio.to_thread(route, message, prior, client)
    except LLMError as exc:
        await asyncio.to_thread(
            repo.log_tool_call, conversation_id, "route_intent", {"message": message},
            status="ERROR", error_type="RETRYABLE", error_message=str(exc)[:500],
            latency_ms=int((time.perf_counter() - route_started) * 1000))
        await asyncio.to_thread(repo.insert_message, conversation_id, "assistant", FALLBACK_ANSWER)
        yield {"type": "token", "value": FALLBACK_ANSWER}
        yield {"type": "done", "intent": None, "degraded": True}
        return

    await asyncio.to_thread(
        repo.log_tool_call, conversation_id, "route_intent", {"message": message},
        result={"intent": result.intent, "confidence": result.confidence,
                "slots": result.slots, "missing_slots": result.missing_slots,
                "standalone_query": result.standalone_query},
        latency_ms=int((time.perf_counter() - route_started) * 1000))
    yield {"type": "intent", "value": result.intent, "confidence": round(result.confidence, 2),
           "needs_clarification": result.needs_clarification}

    # --- Truy hồi tri thức -------------------------------------------------
    chunks: list = []
    if result.intent in RAG_INTENTS or result.intent in ACTION_INTENTS:
        yield {"type": "status", "value": "Đang tra cứu chính sách"}
        rag_started = time.perf_counter()
        try:
            # Truy hồi bằng câu ĐÃ viết lại, không phải tin nhắn thô. Câu nối
            # tiếp kiểu "thế còn xe máy thì sao?" đem tra thẳng sẽ kéo về nhầm
            # tài liệu và agent trả lời sai số liệu.
            chunks = await asyncio.to_thread(retrieve, result.standalone_query, 3, client)
            await asyncio.to_thread(
                repo.log_tool_call, conversation_id, "retrieve_policy",
                {"query": result.standalone_query, "original_message": message, "top_k": 3},
                result={"sources": [c.source_file for c in chunks],
                        "top_similarity": round(chunks[0].similarity, 3) if chunks else None},
                latency_ms=int((time.perf_counter() - rag_started) * 1000))
        except Exception as exc:
            # Truy hồi hỏng không được làm đổ cả lượt — vẫn trả lời được bằng
            # kiến thức chung, chỉ là kém chính xác hơn.
            await asyncio.to_thread(
                repo.log_tool_call, conversation_id, "retrieve_policy",
                {"query": result.standalone_query, "top_k": 3}, status="ERROR",
                error_type="RETRYABLE",
                error_message=str(exc)[:500],
                latency_ms=int((time.perf_counter() - rag_started) * 1000))
            yield {"type": "status", "value": "Không tra cứu được chính sách, trả lời hạn chế"}

    history = await asyncio.to_thread(repo.recent_messages, conversation_id, 8)
    prompt = _build_prompt(message, chunks, history[:-1])

    # --- Sinh câu trả lời (stream) ----------------------------------------
    yield {"type": "status", "value": "Đang soạn câu trả lời"}
    collected: list[str] = []
    ttft_ms: int | None = None
    usage: dict[str, int] = {}
    try:
        async for delta, first_ms, meta in client.astream(
                prompt, system=ANSWER_SYSTEM, max_tokens=700):
            if meta:
                usage = meta
                continue
            if first_ms is not None:
                ttft_ms = first_ms
            collected.append(delta)
            yield {"type": "token", "value": delta}
    except LLMError as exc:
        await asyncio.to_thread(
            repo.log_tool_call, conversation_id, "generate_answer", {"model": client.answer_model},
            status="ERROR", error_type="RETRYABLE", error_message=str(exc)[:500])
        if not collected:
            await asyncio.to_thread(
                repo.insert_message, conversation_id, "assistant", FALLBACK_ANSWER,
                intent=result.intent, intent_confidence=result.confidence)
            yield {"type": "token", "value": FALLBACK_ANSWER}
            yield {"type": "done", "intent": result.intent, "degraded": True}
            return

    answer = mask_text("".join(collected))  # lưới an toàn lớp hai (ADR-004)
    await asyncio.to_thread(
        repo.insert_message, conversation_id, "assistant", answer,
        intent=result.intent, intent_confidence=result.confidence,
        model_name=usage.get("model") or client.answer_model,
        provider=usage.get("provider", "gemini"),
        prompt_tokens=usage.get("prompt_tokens"), completion_tokens=usage.get("completion_tokens"),
        ttft_ms=ttft_ms, latency_ms=int((time.perf_counter() - turn_started) * 1000))

    yield {
        "type": "done",
        "intent": result.intent,
        "ttft_ms": ttft_ms,
        "latency_ms": int((time.perf_counter() - turn_started) * 1000),
        "sources": sorted({c.source_file for c in chunks}),
        "prompt_tokens": usage.get("prompt_tokens"),
        "completion_tokens": usage.get("completion_tokens"),
        "action_pending": result.intent in ACTION_INTENTS,
        "provider": usage.get("provider", "gemini"),
        "degraded": False,
    }
