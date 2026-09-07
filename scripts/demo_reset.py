"""Đưa cơ sở dữ liệu về trạng thái demo được, chạy trước mỗi lần trình bày.

    .venv/Scripts/python.exe -m scripts.demo_reset

Vì sao cần: buổi demo phụ thuộc vào **trạng thái dữ liệu**, mà trạng thái đó bị
các lần chạy test và eval làm biến dạng. Kiểm thực tế ngày 2026-08-26: ca chờ
duyệt `RF-SEED-0001` đã bị test tiêu thụ hết, nên hàng đợi CSKH rỗng trơn —
đúng thứ sẽ làm hỏng phần trình bày quan trọng nhất.

Script này KHÔNG xoá dữ liệu nghiệp vụ (chuyến, khách, kho tri thức). Nó chỉ:
1. dọn hội thoại rác do test sinh ra,
2. dựng lại đúng MỘT ca chờ duyệt để dashboard có thứ để xem,
3. xoá lịch sử hoàn tiền đã duyệt trong tháng, để nhánh tự-duyệt còn chạy được
   trên sân khấu (hạn mức 2 lần/tháng của KB 03 mục 4).
"""
from __future__ import annotations

from src.backend.db.connection import get_connection
from src.backend.db.demo_guard import ensure_demo_operation_allowed

# Tiền tố thread_id do test, eval, và chính script này sinh ra — an toàn để xoá.
# `demo-hitl-seed%` phải nằm trong danh sách, nếu không lần chạy thứ hai sẽ vấp
# ràng buộc UNIQUE trên `thread_id` — script dọn dẹp mà không tự dọn được chính nó
# thì vô dụng, vì nó luôn được chạy lại ngay trước buổi trình bày.
TEST_THREAD_PREFIXES = (
    "pytest-%", "chaos-%", "mt-%", "e2e-%", "graph-%", "hitl-%",
    "pii-%", "pii-test-%", "probe-%", "envcheck-%", "pii-ux%",
    "csat-%", "demo-hitl-seed%", "demo-csat-%",
)

REQUIRED_CASES = [
    "XSM-DOUBLE-01", "XSM-DOUBLE-02", "XSM-DETOUR-01", "XSM-DETOUR-02",
    "XSM-CANCELFEE-01", "XSM-CANCELFEE-02", "XSM-LOSTITEM-01",
    "XSM-FAREDIFF-01", "XSM-VEHICLE-01", "XSM-ACTIVE-01", "XSM-ACTIVE-02",
]


def main() -> None:
    ensure_demo_operation_allowed("ALLOW_DEMO_RESET", "reset dữ liệu demo")
    report: list[str] = []

    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("SELECT id FROM users WHERE email = 'demo.customer@gsm.vn'")
        row = cur.fetchone()
        if not row:
            raise SystemExit("Không tìm thấy tài khoản demo — chạy src.backend.db.seed trước.")
        customer_id = row[0]

        # 1. Dọn hội thoại rác do test sinh ra
        conditions = " OR ".join(["thread_id LIKE %s"] * len(TEST_THREAD_PREFIXES))
        cur.execute(f"SELECT id FROM conversations WHERE {conditions}", TEST_THREAD_PREFIXES)
        junk = [r[0] for r in cur.fetchall()]
        if junk:
            for table in ("refund_requests", "tickets", "tool_calls", "messages"):
                cur.execute(f"DELETE FROM {table} WHERE conversation_id = ANY(%s)", (junk,))
            cur.execute("DELETE FROM conversations WHERE id = ANY(%s)", (junk,))
        report.append(f"Đã xoá {len(junk)} hội thoại rác (test, eval, và lần reset trước)")

        # 2. Xoá lịch sử hoàn tiền để nhánh tự-duyệt còn chạy được trên sân khấu
        cur.execute("SELECT refund_code FROM refund_requests")
        old_codes = [r[0] for r in cur.fetchall()]
        if old_codes:
            cur.execute("DELETE FROM audit_log WHERE entity_id = ANY(%s)", (old_codes,))
            cur.execute("DELETE FROM refund_requests WHERE refund_code = ANY(%s)", (old_codes,))
        report.append(f"Đã xoá {len(old_codes)} yêu cầu hoàn tiền cũ "
                      "(hạn mức 2 lần/tháng nay đã trống)")

        # 3. Dựng lại đúng MỘT ca chờ duyệt cho dashboard
        cur.execute("SELECT id FROM rides WHERE ride_code = 'XSM-DOUBLE-02'")
        ride = cur.fetchone()
        cur.execute(
            "INSERT INTO conversations (customer_id, thread_id, status) "
            "VALUES (%s, 'demo-hitl-seed', 'WAITING_HUMAN') RETURNING id", (customer_id,))
        conversation_id = cur.fetchone()[0]
        cur.execute(
            "INSERT INTO messages (conversation_id, role, content, intent) VALUES "
            "(%s, 'user', %s, 'refund.request'), (%s, 'assistant', %s, 'refund.request')",
            (conversation_id,
             "Chuyến XSM-DOUBLE-02 của tôi bị trừ tiền hai lần, hoàn lại tiền cho tôi",
             conversation_id,
             "Dạ, yêu cầu hoàn tiền 120.000 VNĐ của anh/chị vượt hạn mức em được phép tự "
             "xử lý, nên em đã chuyển tới bộ phận phụ trách để kiểm tra và đối soát ạ."))
        cur.execute(
            "INSERT INTO refund_requests (refund_code, customer_id, ride_id, conversation_id, "
            "amount, reason_code, reason_detail, fraud_score, status, resume_thread_id, "
            "idempotency_key) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,'PENDING_HITL',%s,%s)",
            ("RF-DEMO-0001", customer_id, ride[0] if ride else None, conversation_id, 120_000,
             "DOUBLE_CHARGE",
             "Log thanh toán ghi nhận 2 giao dịch SUCCESS cho cùng chuyến, cách nhau 8 giây.",
             0.12, str(conversation_id), "demo:refund:seed"))
        report.append("Đã dựng 1 ca chờ duyệt: RF-DEMO-0001 · 120.000 VNĐ · thu tiền trùng")

        # 4. Dựng vài điểm hài lòng để ô CSAT trên dashboard có số thật
        # Không có dòng nào thì dashboard hiện "—" ngay giữa lúc trình bày, trông
        # như tính năng chưa làm xong chứ không phải như chưa có ai đánh giá.
        for i, score in enumerate((5, 4, 5, 3), start=1):
            cur.execute(
                "INSERT INTO conversations (customer_id, thread_id, status) "
                "VALUES (%s, %s, 'CLOSED') RETURNING id", (customer_id, f"demo-csat-{i}"))
            conv_id = cur.fetchone()[0]
            cur.execute(
                "INSERT INTO csat_ratings (conversation_id, customer_id, score) "
                "VALUES (%s, %s, %s)", (conv_id, customer_id, score))
        report.append("Đã dựng 4 lượt đánh giá (5·4·5·3 → trung bình 4,25)")

        # 5. Kiểm 11 case khó còn đủ không
        cur.execute("SELECT ride_code FROM rides WHERE ride_code = ANY(%s)", (REQUIRED_CASES,))
        found = {r[0] for r in cur.fetchall()}
        missing = [code for code in REQUIRED_CASES if code not in found]
        report.append(
            f"Case khó: {len(found)}/{len(REQUIRED_CASES)}"
            + (f" — THIẾU {missing}, chạy lại src.backend.db.seed" if missing else " ✓"))

        # 6. Trả các chuyến đang chạy về đúng trạng thái để demo huỷ chuyến
        cur.execute(
            "UPDATE rides SET status = 'ASSIGNED', cancelled_at = NULL, cancel_fee = 0, "
            "cancel_reason = NULL, cancelled_by = NULL, requested_at = now() "
            "WHERE ride_code = 'XSM-ACTIVE-02'")
        cur.execute(
            "UPDATE rides SET status = 'IN_PROGRESS', cancelled_at = NULL "
            "WHERE ride_code = 'XSM-ACTIVE-01'")
        report.append("Đã trả XSM-ACTIVE-01/02 về trạng thái đang chạy (để demo huỷ và đổi điểm)")

        cur.execute("SELECT count(*) FROM knowledge_chunks")
        chunks = cur.fetchone()[0]
        report.append(f"Kho tri thức: {chunks} đoạn"
                      + (" ✓" if chunks > 0 else " — TRỐNG, chạy src.backend.rag.indexer"))

    print("  ĐÃ ĐƯA VỀ TRẠNG THÁI DEMO\n")
    for line in report:
        print(f"   · {line}")
    print("\n  Tài khoản: demo.customer@gsm.vn / agent01@gsm.vn · mật khẩu Demo@123")
    print("  Kịch bản trình bày: docs/DEMO.md")


if __name__ == "__main__":
    main()
