"""Kiểm chứng đầu-cuối vertical slice (T-009).

Cần server đang chạy:
    .venv/Scripts/python.exe -m uvicorn src.backend.main:app --port 8000

Chạy:
    .venv/Scripts/python.exe -m tests.test_e2e_slice

Đây là kịch bản kiểm chứng thật, không phải unit test — nó gọi model thật và
ghi vào DB thật, nên không nằm trong `pytest` mặc định.
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import uuid

import httpx
import websockets

# Mặc định nhắm vào server cục bộ. Trỏ vào bản đã deploy bằng:
#   GSM_BASE=https://<app>.onrender.com GSM_WS=wss://<app>.onrender.com
BASE = os.getenv("GSM_BASE", "http://127.0.0.1:8000").rstrip("/")
WS_BASE = os.getenv("GSM_WS", BASE.replace("https://", "wss://").replace("http://", "ws://"))
PASSWORD = os.getenv("GSM_DEMO_PASSWORD", "Demo@123")

results: list[tuple[bool, str]] = []


def check(ok: bool, label: str, detail: str = "") -> bool:
    results.append((ok, label))
    print(f"  {'✅' if ok else '❌'} {label}" + (f"  → {detail}" if detail else ""))
    return ok


async def main() -> int:
    print("=" * 74)
    print("  KIỂM CHỨNG ĐẦU-CUỐI VERTICAL SLICE (T-009)".center(74))
    print("=" * 74)

    async with httpx.AsyncClient(timeout=60) as http:
        print("\n1. Sức khoẻ dịch vụ")
        r = await http.get(f"{BASE}/api/health")
        check(r.status_code == 200 and r.json()["status"] == "ok", "GET /api/health", str(r.json()))

        print("\n2. Xác thực hai vai trò")
        r = await http.post(f"{BASE}/api/auth/login",
                            json={"email": "demo.customer@gsm.vn", "password": PASSWORD})
        check(r.status_code == 200, "Khách đăng nhập")
        customer = r.json()
        check(customer["role"] == "customer", "JWT mang role=customer", customer["full_name"])

        r = await http.post(f"{BASE}/api/auth/login",
                            json={"email": "agent01@gsm.vn", "password": PASSWORD})
        check(r.status_code == 200 and r.json()["role"] == "agent", "CSKH đăng nhập")
        agent = r.json()

        r = await http.post(f"{BASE}/api/auth/login",
                            json={"email": "demo.customer@gsm.vn", "password": "sai-mat-khau"})
        check(r.status_code == 401, "Sai mật khẩu bị từ chối (401)")

        r = await http.post(f"{BASE}/api/auth/login",
                            json={"email": "khong-ton-tai@gsm.vn", "password": PASSWORD})
        check(r.status_code == 401 and "không đúng" in r.json()["detail"],
              "Email không tồn tại trả cùng thông báo (không lộ email nào có thật)")

        print("\n3. Phân quyền — kiểm ở server, không ở giao diện")
        r = await http.get(f"{BASE}/api/dashboard/summary",
                           headers={"Authorization": f"Bearer {customer['access_token']}"})
        check(r.status_code == 403, "Khách gọi dashboard CSKH → 403")

        r = await http.get(f"{BASE}/api/dashboard/summary",
                           headers={"Authorization": f"Bearer {agent['access_token']}"})
        check(r.status_code == 200, "CSKH gọi dashboard → 200")
        summary_before = r.json()

        r = await http.get(f"{BASE}/api/dashboard/summary")
        check(r.status_code == 401, "Không có token → 401")

        r = await http.get(f"{BASE}/api/dashboard/summary",
                           headers={"Authorization": "Bearer token.gia.mao"})
        check(r.status_code == 401, "Token giả mạo → 401")

    print("\n4. Chat streaming qua WebSocket")
    thread_id = f"e2e-{uuid.uuid4().hex[:8]}"
    url = f"{WS_BASE}/ws/chat?token={customer['access_token']}&thread_id={thread_id}"

    turns = [
        ("Phí hủy chuyến với xe taxi là bao nhiêu tiền?", "fare.inquiry"),
        ("Thế còn xe máy thì sao?", None),  # kiểm tra bộ nhớ hội thoại
    ]
    last_done: dict = {}
    async with websockets.connect(url, max_size=2**22) as ws:
        ready = json.loads(await ws.recv())
        check(ready["type"] == "ready", "Bắt tay WebSocket", ready.get("thread_id", ""))

        for turn_index, (message, expected_intent) in enumerate(turns, 1):
            await ws.send(json.dumps({"message": message}))
            tokens: list[str] = []
            intent_event = None
            done = None
            while True:
                event = json.loads(await asyncio.wait_for(ws.recv(), timeout=90))
                if event["type"] == "intent":
                    intent_event = event
                elif event["type"] == "token":
                    tokens.append(event["value"])
                elif event["type"] == "error":
                    print(f"     lỗi từ server: {event['value']}")
                elif event["type"] == "done":
                    done = event
                    break
            answer = "".join(tokens)
            print(f"\n   Lượt {turn_index}: {message!r}")
            print(f"   → intent {intent_event['value'] if intent_event else '?'} "
                  f"(conf {intent_event['confidence'] if intent_event else '?'})")
            print(f"   → TTFT {done.get('ttft_ms')} ms · {done.get('latency_ms')} ms tổng "
                  f"· nguồn {done.get('sources')}")
            print(f"   → {answer[:180].strip()}...")

            check(bool(answer.strip()), f"Lượt {turn_index}: nhận được câu trả lời")
            if expected_intent:
                check(intent_event and intent_event["value"] == expected_intent,
                      f"Lượt {turn_index}: intent = {expected_intent}",
                      intent_event["value"] if intent_event else "?")
            ttft = done.get("ttft_ms")
            check(ttft is not None and ttft < 3000,
                  f"Lượt {turn_index}: TTFT < 3000 ms", f"{ttft} ms")
            last_done = done

        # Lượt 2 phải hiểu "xe máy" là nói tiếp về phí huỷ -> bộ nhớ hội thoại
        check(last_done.get("intent") in ("fare.inquiry", "policy.faq"),
              "Lượt 2 giữ được ngữ cảnh (không rơi về 'other')",
              str(last_done.get("intent")))

    print("\n5. Ghi vết xuống cơ sở dữ liệu")
    from src.backend.db.connection import get_connection

    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("SELECT id FROM conversations WHERE thread_id = %s", (thread_id,))
        row = cur.fetchone()
        check(row is not None, "Hội thoại được ghi vào bảng conversations")
        conversation_id = str(row[0])

        cur.execute(
            "SELECT role, intent, ttft_ms, prompt_tokens, completion_tokens FROM messages "
            "WHERE conversation_id = %s ORDER BY created_at", (conversation_id,))
        messages = cur.fetchall()
        check(len(messages) == 4, "Đủ 4 dòng messages (2 lượt hỏi + 2 lượt đáp)",
              f"{len(messages)} dòng")
        assistant_rows = [m for m in messages if m[0] == "assistant"]
        check(all(m[1] for m in assistant_rows), "Mọi lượt đáp đều có intent")
        check(all(m[2] and m[2] > 0 for m in assistant_rows), "Mọi lượt đáp đều ghi ttft_ms")
        check(all(m[3] and m[4] for m in assistant_rows), "Mọi lượt đáp đều ghi số token")

        cur.execute(
            "SELECT tool_name, status FROM tool_calls WHERE conversation_id = %s "
            "ORDER BY created_at", (conversation_id,))
        tool_calls = cur.fetchall()
        names = [t[0] for t in tool_calls]
        check(names.count("route_intent") == 2, "Mỗi lượt sinh đúng 1 dòng route_intent",
              f"{names.count('route_intent')} dòng")
        check("retrieve_policy" in names, "Truy hồi RAG được ghi vào tool_calls")
        check(all(t[1] == "SUCCESS" for t in tool_calls), "Không có tool call nào lỗi")

    print("\n6. Dashboard phản ánh dữ liệu vừa sinh")
    async with httpx.AsyncClient(timeout=30) as http:
        r = await http.get(f"{BASE}/api/dashboard/summary",
                           headers={"Authorization": f"Bearer {agent['access_token']}"})
        after = r.json()
        check(after["total_messages"] > summary_before["total_messages"],
              "Số message tăng lên", f"{summary_before['total_messages']} → {after['total_messages']}")
    # p95 của CHÍNH hội thoại vừa chạy. Chỉ số toàn lịch sử trên dashboard gộp cả
    # dữ liệu cũ nên không dùng để nghiệm thu một lần chạy được.
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT max(ttft_ms) FROM messages WHERE conversation_id = %s "
            "AND ttft_ms IS NOT NULL", (conversation_id,))
        worst = cur.fetchone()[0]
    check(worst is not None and worst < 3000,
          "TTFT chậm nhất của lượt vừa chạy < 3000 ms", f"{worst} ms")

    async with httpx.AsyncClient(timeout=30) as http:

        r = await http.get(f"{BASE}/api/conversations/{conversation_id}/transcript",
                           headers={"Authorization": f"Bearer {agent['access_token']}"})
        data = r.json()
        check(len(data["messages"]) == 4 and len(data["tool_calls"]) >= 3,
              "CSKH xem được transcript + tool trace",
              f"{len(data['messages'])} message, {len(data['tool_calls'])} tool call")

    passed = sum(1 for ok, _ in results if ok)
    total = len(results)
    print("\n" + "=" * 74)
    print(f"  {passed}/{total} phép kiểm đạt")
    if passed < total:
        print("  CHƯA ĐẠT:")
        for ok, label in results:
            if not ok:
                print(f"    ❌ {label}")
    print("=" * 74)
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
