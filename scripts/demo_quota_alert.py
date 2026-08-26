"""Bật / tắt cảnh báo vượt hạn mức để trình bày F14.

    .venv/Scripts/python.exe -m scripts.demo_quota_alert on
    .venv/Scripts/python.exe -m scripts.demo_quota_alert off

Vì sao cần: cảnh báo hạn mức chỉ hiện khi dữ liệu **thật** vượt ngưỡng, mà dữ
liệu demo thì không bao giờ vượt. Không có script này thì trên sân khấu chỉ nói
suông được là "có tính năng cảnh báo" — nói suông thì không tính là có.

Script chỉ đụng vào các dòng mang tiền tố `RF-QUOTA-DEMO`, nên `off` không thể
xoá nhầm yêu cầu hoàn tiền thật.
"""
from __future__ import annotations

import sys

from src.backend.db.connection import get_connection

PREFIX = "RF-QUOTA-DEMO"


def main() -> None:
    mode = (sys.argv[1] if len(sys.argv) > 1 else "on").lower()
    if mode not in ("on", "off"):
        raise SystemExit("Dùng: demo_quota_alert on | off")

    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM refund_requests WHERE refund_code LIKE %s", (f"{PREFIX}%",))
        removed = cur.rowcount
        if mode == "off":
            print(f"Đã tắt cảnh báo — xoá {removed} dòng dựng cho demo.")
            return

        cur.execute("SELECT config_value FROM business_config "
                    "WHERE config_key = 'alert.daily_refund_cap_vnd'")
        row = cur.fetchone()
        if not row:
            raise SystemExit("Thiếu khoá alert.daily_refund_cap_vnd — chạy src.backend.db.seed.")
        cap = int(row[0])

        cur.execute("SELECT id FROM users WHERE email = 'demo.customer@gsm.vn'")
        customer = cur.fetchone()
        if not customer:
            raise SystemExit("Không tìm thấy tài khoản demo — chạy src.backend.db.seed trước.")

        # Vượt hẳn 1,5 lần cho rõ, và `decided_at = now()` vì hạn mức tính theo
        # thời điểm duyệt chứ không phải thời điểm tạo yêu cầu.
        amount = cap + cap // 2
        cur.execute(
            "INSERT INTO refund_requests (refund_code, customer_id, amount, reason_code, "
            "reason_detail, status, decided_at, idempotency_key) "
            "VALUES (%s,%s,%s,'DOUBLE_CHARGE',%s,'AUTO_APPROVED',now(),%s)",
            (f"{PREFIX}-01", customer[0], amount,
             "Dòng dựng sẵn để trình bày cảnh báo hạn mức (F14).", f"demo:quota:{PREFIX}-01"))

    print(f"Đã bật cảnh báo: {amount:,} / {cap:,} VNĐ trong ngày.".replace(",", "."))
    print("Mở dashboard CSKH → tab Tổng quan, dải cảnh báo đỏ nằm trên đầu.")
    print("Tắt đi bằng: .venv/Scripts/python.exe -m scripts.demo_quota_alert off")


if __name__ == "__main__":
    main()
