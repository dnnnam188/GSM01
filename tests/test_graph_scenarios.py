"""Kịch bản nghiệp vụ chạy qua LangGraph (T-004).

Chạy: `.venv/Scripts/python.exe -m tests.test_graph_scenarios`

Là kịch bản kiểm chứng, không phải unit test: nó gọi model thật và ghi DB thật,
nên không nằm trong `pytest` mặc định. Mỗi kịch bản kiểm **đường đi trong graph**
(node nào chạy, tool nào được gọi), chứ không chỉ kiểm câu trả lời có chữ nào.
"""
from __future__ import annotations

import asyncio
import sys
import uuid

from src.backend.agent.graph import run_graph
from src.backend.db.connection import get_connection
from src.backend.db.repository import get_business_config, get_user_by_email

results: list[tuple[bool, str]] = []


def check(ok: bool, label: str, detail: str = "") -> bool:
    results.append((ok, label))
    print(f"  {'PASS' if ok else 'FAIL'}  {label}" + (f"  -> {detail}" if detail else ""))
    return ok


def _new_conversation(customer_id: str) -> str:
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("INSERT INTO conversations (customer_id, thread_id) VALUES (%s,%s) "
                    "RETURNING id", (customer_id, f"graph-{uuid.uuid4().hex[:10]}"))
        return str(cur.fetchone()[0])


def _cleanup(conversation_ids: list[str], refund_codes: list[str], ride_codes: list[str]) -> None:
    with get_connection() as conn, conn.cursor() as cur:
        if refund_codes:
            cur.execute("DELETE FROM audit_log WHERE entity_id = ANY(%s)", (refund_codes,))
            cur.execute("DELETE FROM refund_requests WHERE refund_code = ANY(%s)", (refund_codes,))
        if ride_codes:
            cur.execute("DELETE FROM rides WHERE ride_code = ANY(%s)", (ride_codes,))
        cur.execute("DELETE FROM tickets WHERE conversation_id = ANY(%s)", (conversation_ids,))
        cur.execute("DELETE FROM tool_calls WHERE conversation_id = ANY(%s)", (conversation_ids,))
        cur.execute("DELETE FROM messages WHERE conversation_id = ANY(%s)", (conversation_ids,))
        cur.execute("DELETE FROM conversations WHERE id = ANY(%s)", (conversation_ids,))


def tools_called(state) -> list[str]:
    return [c["tool"] for c in (state.get("tool_results") or [])]


async def main() -> int:
    customer = get_user_by_email("demo.customer@gsm.vn")
    cid = customer["id"]
    threshold = get_business_config()["refund.auto_approve_max_vnd"]
    conversations: list[str] = []
    refund_codes: list[str] = []
    ride_codes: list[str] = []

    print("=" * 74)
    print("  KỊCH BẢN NGHIỆP VỤ QUA LANGGRAPH (T-004)".center(74))
    print("=" * 74)

    # --- 1. Hỏi chính sách: chỉ RAG, KHÔNG được gọi tool ghi dữ liệu -------
    print("\n1. policy.faq — chỉ tra chính sách")
    conv = _new_conversation(cid)
    conversations.append(conv)
    s = await run_graph(cid, conv, "Khi nào thì tôi được hủy chuyến miễn phí?", [])
    check(s["intent"] == "policy.faq", "intent = policy.faq", s["intent"])
    check(bool(s.get("chunks")), "có truy hồi tri thức", f"{len(s.get('chunks') or [])} đoạn")
    check(tools_called(s) == [], "KHÔNG gọi tool nào", str(tools_called(s)))
    check("TRI THỨC CHÍNH SÁCH" in s.get("answer_prompt", ""), "prompt có phần tri thức")

    # --- 2. Tra cứu chuyến cụ thể -----------------------------------------
    print("\n2. trip.lookup — có mã chuyến trong câu")
    conv = _new_conversation(cid)
    conversations.append(conv)
    s = await run_graph(cid, conv, "Cho tôi xem chi tiết chuyến XSM-DETOUR-01", [])
    check(s["intent"] == "trip.lookup", "intent = trip.lookup", s["intent"])
    check("get_ride_detail" in tools_called(s), "gọi get_ride_detail", str(tools_called(s)))
    detail = next((c for c in s["tool_results"] if c["tool"] == "get_ride_detail"), None)
    check(detail is not None and detail["ok"], "tool chạy thành công")
    check(detail is not None and "8.4" in str(detail["data"].get("actual_distance_km")),
          "dữ liệu thật vào được prompt", str(detail["data"].get("actual_distance_km")))

    # --- 3. Thiếu mã chuyến -> hỏi lại, TUYỆT ĐỐI không đoán bừa ----------
    print("\n3. complaint.lost_item — thiếu mã chuyến")
    conv = _new_conversation(cid)
    conversations.append(conv)
    s = await run_graph(cid, conv, "Tôi để quên cái ví trên xe", [])
    check(s["intent"] == "complaint.lost_item", "intent = complaint.lost_item", s["intent"])
    created = [c for c in (s.get("tool_results") or []) if c["tool"] == "create_ticket"]
    if s.get("clarify_question"):
        check(True, "hỏi lại thay vì đoán bừa", s["clarify_question"][:60])
        check(created == [], "KHÔNG tạo ticket khi chưa biết chuyến nào")
    else:
        # Suy ra được đúng một chuyến thì đi tiếp là hợp lệ
        check(bool(created) and created[0]["ok"], "suy ra được chuyến và tạo ticket",
              str(created[0]["data"].get("ticket_code")) if created else "")

    # --- 4. Hoàn tiền vượt ngưỡng -> PENDING_HITL -------------------------
    print("\n4. refund.request vượt ngưỡng — phải chặn lại chờ người duyệt")
    conv = _new_conversation(cid)
    conversations.append(conv)
    s = await run_graph(
        cid, conv, "Chuyến XSM-DOUBLE-02 của tôi bị trừ tiền hai lần, hoàn lại cho tôi", [])
    check(s["intent"] == "refund.request", "intent = refund.request", s["intent"])
    check("request_refund" in tools_called(s), "gọi request_refund", str(tools_called(s)))
    refund = next((c for c in s["tool_results"] if c["tool"] == "request_refund"), None)
    if refund and refund["ok"]:
        refund_codes.append(refund["data"]["refund_code"])
        check(refund["data"]["status"] == "PENDING_HITL",
              "trạng thái = PENDING_HITL (không tự duyệt)", refund["data"]["status"])
        check(bool(s.get("pending_hitl")), "graph đánh dấu ca chờ người duyệt")
        check(bool(refund["data"].get("escalation_reason")),
              "có nêu lý do phải chuyển người", str(refund["data"].get("escalation_reason"))[:70])
        check(refund["data"]["amount"] == 120_000,
              "số tiền do HỆ THỐNG suy ra từ bằng chứng, không do khách khai",
              f"{refund['data']['amount']:,} VNĐ")
    else:
        check(False, "request_refund chạy được",
              str(refund["error"]["code"]) if refund else "không gọi")

    # --- 5. Hoàn tiền dưới ngưỡng -> tự duyệt ------------------------------
    print("\n5. refund.request dưới ngưỡng — AI tự duyệt")
    conv = _new_conversation(cid)
    conversations.append(conv)
    s = await run_graph(
        cid, conv, "Chuyến XSM-DOUBLE-01 bị thu trùng tiền, cho tôi xin lại nhé", [])
    refund = next((c for c in (s.get("tool_results") or [])
                   if c["tool"] == "request_refund"), None)
    if refund and refund["ok"]:
        refund_codes.append(refund["data"]["refund_code"])
        check(refund["data"]["status"] == "AUTO_APPROVED",
              "trạng thái = AUTO_APPROVED", refund["data"]["status"])
        check(refund["data"]["amount"] <= threshold,
              "số tiền suy ra nằm dưới ngưỡng tự duyệt", f"{refund['data']['amount']:,} VNĐ")
    else:
        check(False, "request_refund chạy được",
              str(refund["error"]["code"]) if refund else "không gọi")

    # --- 5b. Không đủ điều kiện -> phải TỪ CHỐI, không tạo yêu cầu hoàn tiền
    print("\n5b. refund.request không đủ điều kiện — phải từ chối đúng")
    conv = _new_conversation(cid)
    conversations.append(conv)
    s = await run_graph(
        cid, conv, "Chuyến XSM-CANCELFEE-02 thu phí huỷ của tôi, tôi muốn đòi lại tiền", [])
    elig = next((c for c in (s.get("tool_results") or [])
                 if c["tool"] == "refund_eligibility"), None)
    check(elig is not None and elig["data"].get("eligible") is False,
          "đối soát ra KHÔNG đủ điều kiện", str(elig["data"])[:70] if elig else "thiếu")
    check("request_refund" not in tools_called(s),
          "KHÔNG tạo yêu cầu hoàn tiền cho ca không đủ điều kiện", str(tools_called(s)))

    # --- 6. Câu ngoài phạm vi -> không tra, không gọi tool ----------------
    print("\n6. other — ngoài phạm vi")
    conv = _new_conversation(cid)
    conversations.append(conv)
    s = await run_graph(cid, conv, "Thời tiết Hà Nội hôm nay thế nào?", [])
    check(s["intent"] == "other", "intent = other", s["intent"])
    check(tools_called(s) == [], "không gọi tool", str(tools_called(s)))
    check(not s.get("chunks"), "không truy hồi tri thức")

    # --- 7. Prompt trả lời phải mang KẾT QUẢ THAO TÁC ---------------------
    print("\n7. Prompt trả lời có thuật lại kết quả tool")
    conv = _new_conversation(cid)
    conversations.append(conv)
    s = await run_graph(cid, conv, "Chuyến XSM-FAREDIFF-01 chi tiết ra sao?", [])
    check("KẾT QUẢ THAO TÁC" in s.get("answer_prompt", ""),
          "prompt có mục KẾT QUẢ THAO TÁC")
    check("XSM-FAREDIFF-01" in s.get("answer_prompt", ""), "prompt mang mã chuyến thật")

    _cleanup(conversations, refund_codes, ride_codes)

    passed = sum(1 for ok, _ in results if ok)
    print("\n" + "=" * 74)
    print(f"  {passed}/{len(results)} phép kiểm đạt")
    for ok, label in results:
        if not ok:
            print(f"    FAIL  {label}")
    print("=" * 74)
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
