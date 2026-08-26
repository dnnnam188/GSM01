"""Chaos test: hệ thống hỏng thì phải hỏng ÊM (T-012).

Đề bài yêu cầu "fallback khi tool lỗi". Nhưng chỉ có fallback là chưa đủ — điều
phải chứng minh là khi mọi thứ hỏng, **khách hàng nhận được một câu tử tế chứ
không phải stacktrace**, và sự cố vẫn được ghi lại để truy vết.

Bốn kịch bản, tương ứng bốn tầng có thể sập:
1. Cả hai provider LLM chết
2. Cơ sở dữ liệu chết giữa lúc gọi tool
3. Truy hồi tri thức chết (nhưng LLM còn sống)
4. Tool trả lỗi nghiệp vụ FATAL

Điểm chung của cả bốn: **không được để lộ chi tiết kỹ thuật ra phía khách**.
"""
from __future__ import annotations

import asyncio
import uuid

import httpx
import pytest

from src.backend.db.connection import get_connection
from src.backend.db.repository import get_user_by_email
from src.backend.llm.client import LLMError

# Dấu hiệu của rò rỉ chi tiết kỹ thuật ra câu trả lời cho khách
LEAKY_TOKENS = (
    "Traceback", "Exception", "psycopg", "httpx", "None", "null",
    "SELECT", "INSERT", "conversation_id", "gemini", "api_key", "  File \"",
)


def assert_safe_for_customer(text: str) -> None:
    assert text.strip(), "Khách phải nhận được câu trả lời, không được im lặng"
    for token in LEAKY_TOKENS:
        assert token not in text, f"Lộ chi tiết kỹ thuật ra cho khách: {token!r}"


@pytest.fixture
def conversation() -> str:
    customer = get_user_by_email("demo.customer@gsm.vn")["id"]
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("INSERT INTO conversations (customer_id, thread_id) VALUES (%s,%s) "
                    "RETURNING id", (customer, f"chaos-{uuid.uuid4().hex[:8]}"))
        conversation_id = str(cur.fetchone()[0])
    yield conversation_id
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM tool_calls WHERE conversation_id = %s", (conversation_id,))
        cur.execute("DELETE FROM messages WHERE conversation_id = %s", (conversation_id,))
        cur.execute("DELETE FROM conversations WHERE id = %s", (conversation_id,))


# ---------------------------------------------------------------------------
# 1. Cả hai provider LLM chết
# ---------------------------------------------------------------------------
def test_ca_hai_provider_chet_thi_khach_van_nhan_duoc_cau_xin_loi(monkeypatch, conversation):
    from src.backend.agent import pipeline
    from src.backend.llm.client import LLMClient

    def dead_gemini(*_args, **_kwargs):
        raise httpx.ConnectError("gia lap mat mang toi Gemini")

    def dead_fallback(*_args, **_kwargs):
        raise LLMError("gia lap provider du phong het credit")

    monkeypatch.setattr(LLMClient, "_gemini_stream", dead_gemini)
    monkeypatch.setattr(LLMClient, "_fallback_call", dead_fallback)

    async def dead_astream(*_args, **_kwargs):
        raise LLMError("gia lap ca hai provider deu chet")
        yield  # pragma: no cover

    monkeypatch.setattr(LLMClient, "astream", dead_astream)

    customer = get_user_by_email("demo.customer@gsm.vn")["id"]

    async def run() -> list[dict]:
        events = []
        with get_connection() as conn, conn.cursor() as cur:
            cur.execute("SELECT thread_id FROM conversations WHERE id = %s", (conversation,))
            thread_id = cur.fetchone()[0]
        async for event in pipeline.run_turn(customer, thread_id, "Phí huỷ chuyến bao nhiêu?"):
            events.append(event)
        return events

    events = asyncio.run(run())
    answer = "".join(e["value"] for e in events if e["type"] == "token")
    done = next(e for e in events if e["type"] == "done")

    assert_safe_for_customer(answer)
    assert done["degraded"] is True, "Phải đánh dấu lượt này là trả lời hạn chế"

    # Sự cố phải để lại dấu vết cho người vận hành
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("SELECT tool_name, error_type FROM tool_calls "
                    "WHERE conversation_id = %s AND status = 'ERROR'", (conversation,))
        errors = cur.fetchall()
    assert errors, "Hỏng mà không ghi lại thì không ai biết để sửa"
    assert all(row[1] == "RETRYABLE" for row in errors), errors


# ---------------------------------------------------------------------------
# 2. Cơ sở dữ liệu chết giữa lúc gọi tool
# ---------------------------------------------------------------------------
def test_db_chet_thi_tool_bao_RETRYABLE_va_khong_lo_chi_tiet(monkeypatch, conversation):
    from src.backend.tools import executor

    def dead_db(*_args, **_kwargs):
        raise RuntimeError("connection to server at 10.0.0.1 failed: timeout expired")

    monkeypatch.setattr(executor, "get_connection", dead_db)

    result = executor.execute_tool(
        "get_ride_detail",
        {"conversation_id": conversation, "ride_code": "XSM-LOSTITEM-01"},
        conversation_id=conversation)

    assert not result.ok
    assert result.error.error_type.value == "RETRYABLE", "Lỗi hạ tầng thì phải thử lại được"
    assert_safe_for_customer(result.error.message_for_user)
    # Chi tiết kỹ thuật vẫn phải được giữ lại — nhưng ở nhánh log, không phải nhánh khách
    assert "timeout expired" in (result.error.detail_for_log or "")


# ---------------------------------------------------------------------------
# 3. Truy hồi tri thức chết nhưng LLM còn sống
# ---------------------------------------------------------------------------
def test_truy_hoi_chet_thi_van_tra_loi_duoc_chi_la_han_che(monkeypatch, conversation):
    from src.backend.agent import graph

    def dead_retrieve(*_args, **_kwargs):
        raise ConnectionError("gia lap pgvector khong phan hoi")

    monkeypatch.setattr(graph, "retrieve", dead_retrieve)

    state = graph.retrieve_node({
        "conversation_id": conversation,
        "message": "Phí huỷ chuyến bao nhiêu?",
        "standalone_query": "Phí huỷ chuyến bao nhiêu?",
    })

    assert state["chunks"] == []
    assert state["degraded"] is True, "Phải tự đánh dấu là đang trả lời thiếu căn cứ"

    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("SELECT status, error_type FROM tool_calls WHERE conversation_id = %s "
                    "AND tool_name = 'retrieve_policy'", (conversation,))
        row = cur.fetchone()
    assert row == ("ERROR", "RETRYABLE")


# ---------------------------------------------------------------------------
# 4. Tool trả lỗi nghiệp vụ — không được nói dối là đã làm xong
# ---------------------------------------------------------------------------
def test_loi_nghiep_vu_FATAL_thi_khong_thu_lai_va_giai_thich_duoc(conversation):
    from src.backend.tools.executor import execute_tool

    result = execute_tool(
        "cancel_ride",
        {"conversation_id": conversation, "ride_code": "XSM-LOSTITEM-01",
         "reason": "Thu huy chuyen da hoan thanh"},
        conversation_id=conversation)

    assert not result.ok
    assert result.error.error_type.value == "FATAL", "Sai về bản chất thì thử lại vô ích"
    assert result.error.code == "ALREADY_COMPLETED"
    assert_safe_for_customer(result.error.message_for_user)
    # Thông báo phải nói được VÌ SAO, không chỉ nói là hỏng
    assert "hoàn thành" in result.error.message_for_user


def test_moi_su_co_deu_de_lai_dau_vet_trong_tool_calls(conversation):
    """Không có dòng log thì tool trace của CSKH bị thủng đúng chỗ cần nhất."""
    from src.backend.tools.executor import execute_tool

    execute_tool("get_ride_detail",
                 {"conversation_id": conversation, "ride_code": "XSM-KHONG-TON-TAI"},
                 conversation_id=conversation)

    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("SELECT status, error_type, error_message FROM tool_calls "
                    "WHERE conversation_id = %s ORDER BY created_at DESC LIMIT 1",
                    (conversation,))
        row = cur.fetchone()
    assert row is not None, "Tool hỏng mà không ghi log"
    assert row[0] == "ERROR" and row[1] == "FATAL"
    assert row[2], "Phải giữ lại nội dung lỗi để người vận hành đọc"
