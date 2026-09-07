"""Kiểm chứng trọn luồng Human-in-the-loop (T-011, ADR-003).

Cần server đang chạy:
    .venv/Scripts/python.exe -m uvicorn src.backend.main:app --port 8000

Chạy:
    .venv/Scripts/python.exe -m tests.test_hitl_flow

Điều kịch bản này chứng minh — và cũng là khác biệt lớn nhất so với cách làm phổ
thông ("tạo ticket rồi kết thúc hội thoại"): graph **dừng thật** giữa chừng, trạng
thái nằm trong checkpoint Postgres, và khi CSKH duyệt thì nó **chạy tiếp từ đúng
chỗ dừng**, kết quả hiện lên chính khung chat mà khách đang mở.
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import uuid

import httpx
import websockets

BASE = os.getenv("GSM_BASE", "http://127.0.0.1:8000").rstrip("/")
WS_BASE = os.getenv("GSM_WS", BASE.replace("https://", "wss://").replace("http://", "ws://"))
PASSWORD = os.getenv("GSM_DEMO_PASSWORD", "")

results: list[tuple[bool, str]] = []


def check(ok: bool, label: str, detail: str = "") -> bool:
    results.append((ok, label))
    print(f"  {'✅' if ok else '❌'} {label}" + (f"  → {detail}" if detail else ""))
    return ok


async def _drain_until_done(ws) -> tuple[str, dict]:
    tokens: list[str] = []
    while True:
        event = json.loads(await asyncio.wait_for(ws.recv(), timeout=120))
        if event["type"] == "token":
            tokens.append(event["value"])
        elif event["type"] == "done":
            return "".join(tokens), event
        elif event["type"] == "error":
            print(f"     lỗi từ server: {event['value']}")


async def main() -> int:
    if not PASSWORD:
        raise SystemExit("Đặt GSM_DEMO_PASSWORD khi chạy HITL trên staging; không dùng mật khẩu mặc định.")
    print("=" * 74)
    print("  LUỒNG HUMAN-IN-THE-LOOP (T-011)".center(74))
    print("=" * 74)

    async with httpx.AsyncClient(timeout=120) as http:
        customer = (await http.post(f"{BASE}/api/auth/login",
                    json={"email": "demo.customer@gsm.vn", "password": PASSWORD})).json()
        agent = (await http.post(f"{BASE}/api/auth/login",
                 json={"email": "agent01@gsm.vn", "password": PASSWORD})).json()
        agent_headers = {"Authorization": f"Bearer {agent['access_token']}"}

        print("\n1. Phân quyền hàng đợi duyệt")
        r = await http.get(f"{BASE}/api/hitl/queue",
                           headers={"Authorization": f"Bearer {customer['access_token']}"})
        check(r.status_code == 403, "Khách gọi hàng đợi HITL → 403")
        r = await http.get(f"{BASE}/api/hitl/queue", headers=agent_headers)
        check(r.status_code == 200, "CSKH gọi hàng đợi → 200")
        before = {item["refund_code"] for item in r.json()["pending"]}
        r = await http.post(
            f"{BASE}/api/auth/ws-ticket",
            headers={"Authorization": f"Bearer {customer['access_token']}"},
        )
        check(r.status_code == 200, "Cấp ticket WebSocket dùng một lần")
        ws_ticket = r.json()["ticket"]

    thread_id = f"hitl-{uuid.uuid4().hex[:8]}"
    url = f"{WS_BASE}/ws/chat?thread_id={thread_id}"

    from src.backend.db.connection import get_connection

    print("\n2. Khách yêu cầu hoàn tiền vượt ngưỡng → graph phải DỪNG")
    async with websockets.connect(url, max_size=2**22) as ws:
        await ws.send(json.dumps({"type": "auth", "ticket": ws_ticket}))
        await ws.recv()
        await ws.send(json.dumps({
            "message": "Chuyến XSM-DOUBLE-02 của tôi bị trừ tiền hai lần, hoàn lại tiền cho tôi"}))
        answer, done = await _drain_until_done(ws)
        print(f"     → {answer[:150].strip()}")

        check(done.get("awaiting_human") is True,
              "Lượt kết thúc ở trạng thái chờ người duyệt", str(done.get("awaiting_human")))
        payload = done.get("pending_hitl") or {}
        refund_code = payload.get("refund_code")
        check(bool(refund_code), "Có mã yêu cầu hoàn tiền", str(refund_code))
        check(payload.get("amount") == 120_000,
              "Số tiền do hệ thống suy ra từ bằng chứng", f"{payload.get('amount')}")
        check("chuyển" in answer.lower() and "duyệt" not in answer.lower().split("chuyển")[0],
              "Không hứa chắc là sẽ được duyệt")

        with get_connection() as conn, conn.cursor() as cur:
            cur.execute("SELECT id, status FROM conversations WHERE thread_id = %s", (thread_id,))
            conv_row = cur.fetchone()
            conversation_id = str(conv_row[0])
            check(conv_row[1] == "WAITING_HUMAN",
                  "Hội thoại chuyển sang WAITING_HUMAN", conv_row[1])
            cur.execute("SELECT status, decided_at, resume_thread_id FROM refund_requests "
                        "WHERE refund_code = %s", (refund_code,))
            rr = cur.fetchone()
            check(rr[0] == "PENDING_HITL", "Yêu cầu ở trạng thái PENDING_HITL", rr[0])
            check(rr[1] is None, "Chưa ai duyệt thì không có thời điểm quyết định")
            check(rr[2] == conversation_id, "Đã lưu thread để đánh thức lại graph")
            cur.execute(
                "SELECT count(*) FROM checkpoints WHERE thread_id = %s", (conversation_id,))
            check(cur.fetchone()[0] > 0,
                  "Trạng thái graph đã nằm trong checkpoint Postgres (sống sót restart)")

        print("\n3. Hàng đợi CSKH thấy ca mới")
        async with httpx.AsyncClient(timeout=60) as http:
            r = await http.get(f"{BASE}/api/hitl/queue", headers=agent_headers)
            codes = {item["refund_code"] for item in r.json()["pending"]}
            check(refund_code in codes and refund_code not in before,
                  "Ca mới xuất hiện trong hàng đợi duyệt")
            item = next(i for i in r.json()["pending"] if i["refund_code"] == refund_code)
            check(bool(item.get("reason_detail")),
                  "CSKH thấy được căn cứ đối soát", str(item.get("reason_code")))

            print("\n4. Từ chối mà không nêu lý do phải bị chặn")
            r = await http.post(f"{BASE}/api/hitl/{refund_code}/decide",
                                headers=agent_headers, json={"approved": False, "reason": "  "})
            check(r.status_code == 400, "Từ chối không lý do → 400", str(r.status_code))

            print("\n5. CSKH duyệt → graph chạy tiếp và đẩy kết quả về khách")
            decide = asyncio.create_task(http.post(
                f"{BASE}/api/hitl/{refund_code}/decide", headers=agent_headers,
                json={"approved": True, "reason": "Log thanh toán xác nhận trừ hai lần"}))

            pushed = None
            while True:
                event = json.loads(await asyncio.wait_for(ws.recv(), timeout=150))
                if event["type"] == "hitl_result":
                    pushed = event
                    break
            r = await decide
            body = r.json()

        check(r.status_code == 200, "API duyệt trả 200", str(r.status_code))
        check(body.get("resumed") is True, "Graph đã được đánh thức")
        check(pushed is not None and pushed.get("approved") is True,
              "Khách nhận thông báo NGAY trên phiên đang mở")
        print(f"     → {pushed['message'][:200].strip()}")
        check(body.get("delivered_to_customer", 0) >= 1,
              "Server xác nhận đã đẩy tới khách", str(body.get("delivered_to_customer")))

    print("\n6. Ghi vết sau khi duyệt")
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("SELECT status, decided_by, decision_reason, decided_at "
                    "FROM refund_requests WHERE refund_code = %s", (refund_code,))
        rr = cur.fetchone()
        check(rr[0] == "APPROVED", "Trạng thái → APPROVED", rr[0])
        check(rr[1] is not None, "Ghi rõ ai đã duyệt")
        check(rr[3] is not None, "Ghi rõ thời điểm quyết định")

        cur.execute("SELECT actor_type, action FROM audit_log WHERE entity_id = %s "
                    "ORDER BY created_at DESC LIMIT 1", (refund_code,))
        audit = cur.fetchone()
        check(audit is not None and audit[0] == "HUMAN_AGENT",
              "audit_log ghi hành động của NGƯỜI, không phải AI", str(audit))

        cur.execute("SELECT count(*) FROM refund_requests WHERE resume_thread_id = %s",
                    (conversation_id,))
        count = cur.fetchone()[0]
        check(count == 1,
              "Chỉ có ĐÚNG MỘT yêu cầu hoàn tiền — node chạy lại nhưng idempotency chặn (ADR-005)",
              f"{count} bản ghi")

        cur.execute("SELECT status FROM conversations WHERE id = %s", (conversation_id,))
        check(cur.fetchone()[0] == "ACTIVE", "Hội thoại trở lại ACTIVE")

        cur.execute("SELECT count(*) FROM messages WHERE conversation_id = %s "
                    "AND role = 'assistant'", (conversation_id,))
        check(cur.fetchone()[0] >= 2,
              "Câu trả lời sau duyệt đã được lưu (khách offline vẫn thấy khi quay lại)")

    print("\n7. Duyệt lại lần hai phải bị chặn")
    async with httpx.AsyncClient(timeout=60) as http:
        r = await http.post(f"{BASE}/api/hitl/{refund_code}/decide",
                            headers=agent_headers, json={"approved": True})
        check(r.status_code == 409, "Duyệt trùng → 409", str(r.status_code))

    print("\n8. Ca không còn checkpoint để đánh thức — quyết định KHÔNG được mất")
    # Dựng ca chờ duyệt bằng SQL, tức không có checkpoint LangGraph nào. Trước khi
    # vá, đường này trả HTTP 500 SAU KHI đã ghi quyết định vào DB — hệ thống ghi
    # nhận đã duyệt mà khách không hề được báo. Đó là kiểu hỏng tệ nhất: im lặng
    # và lệch dữ liệu.
    orphan = f"RF-ORPHAN-{uuid.uuid4().hex[:6].upper()}"
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("SELECT id FROM users WHERE email = 'demo.customer@gsm.vn'")
        customer_uuid = cur.fetchone()[0]
        cur.execute("INSERT INTO conversations (customer_id, thread_id, status) "
                    "VALUES (%s, %s, 'WAITING_HUMAN') RETURNING id",
                    (customer_uuid, f"orphan-{uuid.uuid4().hex[:8]}"))
        orphan_conv = str(cur.fetchone()[0])
        cur.execute(
            "INSERT INTO refund_requests (refund_code, customer_id, conversation_id, amount, "
            "reason_code, reason_detail, status, resume_thread_id, idempotency_key) "
            "VALUES (%s,%s,%s,%s,'DOUBLE_CHARGE','Ca khong co checkpoint',"
            "'PENDING_HITL',%s,%s)",
            (orphan, customer_uuid, orphan_conv, 88_000, orphan_conv, f"orphan:{orphan}"))

    async with httpx.AsyncClient(timeout=150) as http:
        r = await http.post(f"{BASE}/api/hitl/{orphan}/decide", headers=agent_headers,
                            json={"approved": True, "reason": "Doi soat xong"})
    check(r.status_code == 200, "Không sập khi không đánh thức được graph", str(r.status_code))
    if r.status_code == 200:
        body = r.json()
        check(body["status"] == "APPROVED", "Quyết định vẫn được ghi nhận")
        check(body["resumed"] is False, "Báo trung thực là graph KHÔNG chạy tiếp được")
        check(bool(body.get("message")), "Khách vẫn nhận được thông báo")

    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("SELECT status FROM refund_requests WHERE refund_code = %s", (orphan,))
        check(cur.fetchone()[0] == "APPROVED", "DB ghi APPROVED, không mất quyết định")
        cur.execute("SELECT count(*) FROM tool_calls WHERE conversation_id = %s "
                    "AND tool_name = 'resume_graph' AND status = 'ERROR'", (orphan_conv,))
        check(cur.fetchone()[0] == 1, "Sự cố đánh thức được ghi lại để truy vết")
        cur.execute("DELETE FROM audit_log WHERE entity_id = %s", (orphan,))
        cur.execute("DELETE FROM refund_requests WHERE refund_code = %s", (orphan,))
        cur.execute("DELETE FROM tool_calls WHERE conversation_id = %s", (orphan_conv,))
        cur.execute("DELETE FROM messages WHERE conversation_id = %s", (orphan_conv,))
        cur.execute("DELETE FROM conversations WHERE id = %s", (orphan_conv,))

    passed = sum(1 for ok, _ in results if ok)
    print("\n" + "=" * 74)
    print(f"  {passed}/{len(results)} phép kiểm đạt")
    for ok, label in results:
        if not ok:
            print(f"    ❌ {label}")
    print("=" * 74)
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
