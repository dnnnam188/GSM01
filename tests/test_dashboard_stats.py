"""Đối soát số liệu dashboard và cảnh báo hạn mức (T-014 · F13, F14).

    .venv/Scripts/python.exe -m pytest tests/test_dashboard_stats.py -q

Nguyên tắc của bộ kiểm này: **không tin con số nào do chính hàm thống kê trả về**.
Mỗi chỉ số được tính lại bằng một truy vấn viết độc lập rồi mới đem so. Một
dashboard lệch với DB còn tệ hơn không có dashboard, vì CSKH sẽ ra quyết định
dựa trên số sai mà không hề biết.
"""
from __future__ import annotations

import uuid

import pytest

from src.backend.db.connection import get_connection
from src.backend.db.repository import dashboard_stats

VN = "Asia/Ho_Chi_Minh"
DAY_START = f"(date_trunc('day', now() AT TIME ZONE '{VN}') AT TIME ZONE '{VN}')"


def q(sql: str, params: tuple = ()):
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchone()


@pytest.fixture(scope="module")
def stats():
    return dashboard_stats()


def test_ticket_khop_db(stats):
    open_, total = q("SELECT count(*) FILTER (WHERE status='OPEN'), count(*) FROM tickets")
    assert stats["tickets"] == {"open": open_, "total": total}


def test_csat_khop_db(stats):
    count, avg = q("SELECT count(*), avg(score) FROM csat_ratings")
    assert stats["csat"]["count"] == count
    if count == 0:
        # Chưa có T-015 nên bảng rỗng. Phải trả None chứ không được trả 0 —
        # "0 điểm hài lòng" và "chưa ai đánh giá" là hai chuyện khác hẳn nhau.
        assert stats["csat"]["average"] is None
    else:
        assert stats["csat"]["average"] == pytest.approx(float(avg), abs=0.01)


def test_token_trong_ngay_khop_db(stats):
    (tokens,) = q(
        "SELECT coalesce(sum(coalesce(prompt_tokens,0)+coalesce(completion_tokens,0)),0) "
        f"FROM messages WHERE created_at >= {DAY_START}")
    assert stats["tokens_today"] == int(tokens)


def test_moc_ngay_theo_gio_viet_nam():
    """DB chạy GMT. Nếu cắt ngày theo GMT thì hạn mức reset lúc 7h sáng giờ VN."""
    row = q(f"SELECT {DAY_START}, date_trunc('day', now())")
    vn_start, gmt_start = row
    assert vn_start.utcoffset().total_seconds() == 0  # vẫn là timestamptz
    # Hai mốc chỉ trùng nhau khi DB đã chạy sẵn giờ VN; ở Neon (GMT) phải lệch.
    (tz,) = q("SELECT current_setting('TimeZone')")
    if tz in ("GMT", "UTC"):
        assert vn_start != gmt_start, "mốc ngày vẫn đang cắt theo GMT"


def test_bieu_do_intent_khop_db(stats):
    (total,) = q("SELECT count(*) FROM messages WHERE intent IS NOT NULL")
    assert sum(r["count"] for r in stats["by_intent"]) == total
    counts = [r["count"] for r in stats["by_intent"]]
    assert counts == sorted(counts, reverse=True), "phải xếp giảm dần"


def test_bieu_do_7_ngay_du_cot(stats):
    daily = stats["daily"]
    assert len(daily) == 7, "ngày không có hoạt động vẫn phải có cột 0"
    (tokens_today,) = q(
        "SELECT coalesce(sum(coalesce(prompt_tokens,0)+coalesce(completion_tokens,0)),0) "
        f"FROM messages WHERE created_at >= {DAY_START}")
    assert daily[-1]["tokens"] == int(tokens_today)


def test_ty_le_tu_xu_ly_nam_trong_khoang_hop_le(stats):
    a = stats["auto_resolve"]
    assert a["escalated"] <= a["answered"]
    if a["answered"]:
        assert 0 <= a["rate_percent"] <= 100
        assert a["rate_percent"] == pytest.approx(
            (a["answered"] - a["escalated"]) / a["answered"] * 100, abs=0.05)


def test_canh_bao_doc_nguong_tu_db(stats):
    keys = {a["key"] for a in stats["alerts"]}
    assert keys == {"refund", "token"}
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("SELECT config_key, config_value FROM business_config "
                    "WHERE config_key LIKE 'alert.%'")
        caps = {k: int(v) for k, v in cur.fetchall()}
    by_key = {a["key"]: a for a in stats["alerts"]}
    assert by_key["refund"]["cap"] == caps["alert.daily_refund_cap_vnd"]
    assert by_key["token"]["cap"] == caps["alert.daily_token_cap"]


def test_bom_du_lieu_vuot_nguong_thi_canh_bao_do():
    """Nghiệm thu F14: bơm dữ liệu vượt ngưỡng → phải nhảy lên mức DANGER.

    Kiểm bằng dữ liệu thật ghi vào DB rồi xoá đi, chứ không giả lập hàm — cảnh báo
    mà chỉ đúng trên hàm giả thì tới lúc có sự cố thật nó vẫn im.
    """
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("SELECT id FROM users WHERE email = 'demo.customer@gsm.vn'")
        customer_id = cur.fetchone()[0]
        cur.execute("SELECT config_value FROM business_config "
                    "WHERE config_key = 'alert.daily_refund_cap_vnd'")
        cap = int(cur.fetchone()[0])

    before = {a["key"]: a for a in dashboard_stats()["alerts"]}["refund"]
    assert before["level"] == "OK", "dữ liệu nền đã vượt ngưỡng sẵn, không kiểm được"

    code = f"RF-ALERT-{uuid.uuid4().hex[:6].upper()}"
    try:
        with get_connection() as conn, conn.cursor() as cur:
            cur.execute(
                "INSERT INTO refund_requests (refund_code, customer_id, amount, reason_code, "
                "status, decided_at, idempotency_key) VALUES "
                "(%s,%s,%s,'DOUBLE_CHARGE','AUTO_APPROVED',now(),%s)",
                (code, customer_id, cap + cap // 2, f"test:alert:{code}"))

        after = {a["key"]: a for a in dashboard_stats()["alerts"]}["refund"]
        assert after["level"] == "DANGER", f"vượt ngưỡng mà không cảnh báo: {after}"
        assert after["current"] > after["cap"]
        assert after["ratio_percent"] >= 150
    finally:
        with get_connection() as conn, conn.cursor() as cur:
            cur.execute("DELETE FROM refund_requests WHERE refund_code = %s", (code,))

    # Xoá xong phải tự hạ cảnh báo — cảnh báo kẹt ở mức đỏ cũng vô dụng
    # như cảnh báo không bao giờ bật.
    assert {a["key"]: a for a in dashboard_stats()["alerts"]}["refund"]["level"] == "OK"


def test_muc_canh_bao_som_o_80_phan_tram():
    """Ba mức chứ không phải hai: chạm 80% đã phải nhắc, đợi vượt là muộn."""
    from src.backend.db.repository import _quota_alert
    assert _quota_alert("k", "l", 79, 100, "u")["level"] == "OK"
    assert _quota_alert("k", "l", 80, 100, "u")["level"] == "WARN"
    assert _quota_alert("k", "l", 100, 100, "u")["level"] == "DANGER"
    assert _quota_alert("k", "l", 5, 0, "u") is None, "không có ngưỡng thì không cảnh báo"
