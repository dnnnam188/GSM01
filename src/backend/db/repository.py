"""Truy cập dữ liệu cho tầng hội thoại.

Mọi hàm ở đây đều đồng bộ (psycopg sync). Tầng API bọc chúng trong
`asyncio.to_thread` để không chặn event loop của FastAPI.
"""
from __future__ import annotations

import json
from typing import Any

import psycopg

from src.backend.db.connection import get_connection


def get_user_by_email(email: str) -> dict[str, Any] | None:
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT id, email, password_hash, role, full_name, is_active "
            "FROM users WHERE lower(email) = lower(%s)", (email,))
        row = cur.fetchone()
    if not row:
        return None
    return {"id": str(row[0]), "email": row[1], "password_hash": row[2],
            "role": row[3], "full_name": row[4], "is_active": row[5]}


def get_user_by_id(user_id: str) -> dict[str, Any] | None:
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("SELECT id, email, role, full_name FROM users WHERE id = %s", (user_id,))
        row = cur.fetchone()
    if not row:
        return None
    return {"id": str(row[0]), "email": row[1], "role": row[2], "full_name": row[3]}


def get_or_create_conversation(customer_id: str, thread_id: str) -> str:
    """Trả về conversation_id. `thread_id` là khoá resume LangGraph sau HITL (ADR-003)."""
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("SELECT id FROM conversations WHERE thread_id = %s", (thread_id,))
        row = cur.fetchone()
        if row:
            cur.execute("UPDATE conversations SET last_activity_at = now() WHERE id = %s", (row[0],))
            return str(row[0])
        cur.execute(
            "INSERT INTO conversations (customer_id, thread_id) VALUES (%s, %s) RETURNING id",
            (customer_id, thread_id))
        return str(cur.fetchone()[0])


def insert_message(conversation_id: str, role: str, content: str, *,
                   intent: str | None = None, intent_confidence: float | None = None,
                   model_name: str | None = None, provider: str | None = None,
                   prompt_tokens: int | None = None, completion_tokens: int | None = None,
                   ttft_ms: int | None = None, latency_ms: int | None = None) -> str:
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO messages (conversation_id, role, content, intent, intent_confidence, "
            "model_name, provider, prompt_tokens, completion_tokens, ttft_ms, latency_ms) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id",
            (conversation_id, role, content, intent, intent_confidence, model_name, provider,
             prompt_tokens, completion_tokens, ttft_ms, latency_ms))
        return str(cur.fetchone()[0])


def log_tool_call(conversation_id: str | None, tool_name: str, arguments: dict, *,
                  result: dict | None = None, status: str = "SUCCESS",
                  error_type: str | None = None, error_message: str | None = None,
                  idempotency_key: str | None = None, latency_ms: int | None = None,
                  message_id: str | None = None) -> str | None:
    """Ghi một dòng vào `tool_calls` (F10).

    Trả về None khi `idempotency_key` đã tồn tại — nghĩa là lời gọi bị chặn vì
    trùng (ADR-005). Nơi gọi phải coi đó là tín hiệu "đã làm rồi", không phải lỗi.
    """
    with get_connection() as conn, conn.cursor() as cur:
        try:
            cur.execute(
                "INSERT INTO tool_calls (conversation_id, message_id, tool_name, arguments, "
                "result, status, error_type, error_message, idempotency_key, latency_ms) "
                "VALUES (%s,%s,%s,%s::jsonb,%s::jsonb,%s,%s,%s,%s,%s) RETURNING id",
                (conversation_id, message_id, tool_name,
                 json.dumps(arguments, ensure_ascii=False),
                 json.dumps(result, ensure_ascii=False) if result is not None else None,
                 status, error_type, error_message, idempotency_key, latency_ms))
            return str(cur.fetchone()[0])
        except psycopg.errors.UniqueViolation:
            return None


def recent_messages(conversation_id: str, limit: int = 8) -> list[dict[str, Any]]:
    """Bộ nhớ ngắn hạn: N lượt gần nhất, trả theo thứ tự thời gian tăng dần."""
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT role, content FROM messages WHERE conversation_id = %s "
            "ORDER BY created_at DESC LIMIT %s", (conversation_id, limit))
        rows = cur.fetchall()
    return [{"role": r[0], "content": r[1]} for r in reversed(rows)]


def conversation_transcript(conversation_id: str) -> dict[str, Any]:
    """Transcript + tool trace của một hội thoại — dashboard CSKH dùng (F12)."""
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT role, content, intent, ttft_ms, created_at FROM messages "
            "WHERE conversation_id = %s ORDER BY created_at", (conversation_id,))
        messages = [
            {"role": r[0], "content": r[1], "intent": r[2], "ttft_ms": r[3],
             "created_at": r[4].isoformat()}
            for r in cur.fetchall()
        ]
        cur.execute(
            "SELECT tool_name, arguments, result, status, error_type, latency_ms, created_at "
            "FROM tool_calls WHERE conversation_id = %s ORDER BY created_at", (conversation_id,))
        tool_calls = [
            {"tool_name": r[0], "arguments": r[1], "result": r[2], "status": r[3],
             "error_type": r[4], "latency_ms": r[5], "created_at": r[6].isoformat()}
            for r in cur.fetchall()
        ]
    return {"messages": messages, "tool_calls": tool_calls}


def dashboard_summary() -> dict[str, Any]:
    """Số liệu tổng quan cho CSKH. Bản đầy đủ làm ở T-005/T-014."""
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM refund_requests WHERE status = 'PENDING_HITL'")
        pending_hitl = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM tickets WHERE status = 'OPEN'")
        open_tickets = cur.fetchone()[0]
        cur.execute(
            "SELECT count(*), coalesce(sum(coalesce(prompt_tokens,0) + "
            "coalesce(completion_tokens,0)), 0) FROM messages")
        total_messages, total_tokens = cur.fetchone()
        cur.execute("SELECT intent, count(*) FROM messages WHERE intent IS NOT NULL "
                    "GROUP BY intent ORDER BY 2 DESC")
        by_intent = {r[0]: r[1] for r in cur.fetchall()}
        cur.execute("SELECT percentile_disc(0.95) WITHIN GROUP (ORDER BY ttft_ms) "
                    "FROM messages WHERE ttft_ms IS NOT NULL")
        p95 = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM tool_calls")
        tool_call_count = cur.fetchone()[0]
    return {"pending_hitl": pending_hitl, "open_tickets": open_tickets,
            "total_messages": total_messages, "total_tokens": int(total_tokens),
            "tool_calls": tool_call_count, "messages_by_intent": by_intent,
            "ttft_p95_ms": p95}


def get_business_config() -> dict[str, Any]:
    """Ngưỡng nghiệp vụ đọc lúc chạy, không hardcode (ADR-006)."""
    casts = {"int": int, "float": float, "bool": lambda v: v.lower() == "true"}
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("SELECT config_key, config_value, value_type FROM business_config")
        return {k: casts.get(t, str)(v) for k, v, t in cur.fetchall()}


def set_conversation_status(conversation_id: str, status: str) -> None:
    """`WAITING_HUMAN` là tín hiệu cho dashboard CSKH biết ca này đang chờ người duyệt."""
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("UPDATE conversations SET status = %s, last_activity_at = now() "
                    "WHERE id = %s", (status, conversation_id))


def hitl_queue(limit: int = 50) -> list[dict[str, Any]]:
    """Hàng đợi yêu cầu hoàn tiền đang chờ CSKH duyệt (F12)."""
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT rr.refund_code, rr.amount, rr.reason_code, rr.reason_detail, "
            "       rr.fraud_score, rr.created_at, rr.resume_thread_id, rr.conversation_id, "
            "       u.full_name, u.email, r.ride_code "
            "FROM refund_requests rr "
            "JOIN users u ON u.id = rr.customer_id "
            "LEFT JOIN rides r ON r.id = rr.ride_id "
            "WHERE rr.status = 'PENDING_HITL' ORDER BY rr.created_at LIMIT %s", (limit,))
        return [
            {"refund_code": r[0], "amount": r[1], "reason_code": r[2], "reason_detail": r[3],
             "fraud_score": float(r[4]), "created_at": r[5].isoformat(),
             "resume_thread_id": r[6],
             "conversation_id": str(r[7]) if r[7] else None,
             "customer_name": r[8], "customer_email": r[9], "ride_code": r[10]}
            for r in cur.fetchall()
        ]


def decide_refund(refund_code: str, *, approved: bool, agent_id: str,
                  reason: str | None) -> dict[str, Any] | None:
    """Ghi quyết định của CSKH. Trả về None nếu ca không còn ở trạng thái chờ.

    Ràng buộc `refund_reject_needs_reason` ở tầng DB bảo đảm từ chối phải có lý do —
    giao diện không thể "quên" áp dụng (xem docs/DATA-MODEL.md mục 3).
    """
    status = "APPROVED" if approved else "REJECTED"
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            "UPDATE refund_requests SET status = %s, decided_by = %s, decision_reason = %s, "
            "decided_at = now() WHERE refund_code = %s AND status = 'PENDING_HITL' "
            "RETURNING amount, resume_thread_id, conversation_id, customer_id",
            (status, agent_id, reason, refund_code))
        row = cur.fetchone()
        if not row:
            return None
        cur.execute(
            "INSERT INTO audit_log (actor_type, actor_id, action, entity_type, entity_id, "
            "after_data, reason) VALUES ('HUMAN_AGENT', %s, %s, 'refund_requests', %s, "
            "%s::jsonb, %s)",
            (agent_id, f"REFUND_{status}", refund_code,
             json.dumps({"status": status, "amount": row[0]}), reason))
    return {"amount": row[0], "resume_thread_id": row[1],
            "conversation_id": str(row[2]) if row[2] else None,
            "customer_id": str(row[3]), "status": status}
