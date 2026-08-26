"""Kiểm thử 8 tool nghiệp vụ trên DB thật.

Đây là kiểm thử tích hợp: nó ghi vào Neon rồi tự dọn. Chạy cùng `pytest`.
Ba nhóm quan trọng nhất là ngưỡng HITL, chống gọi trùng, và tính phí huỷ —
đó là những chỗ mà làm sai thì mất tiền thật.
"""
from __future__ import annotations

import uuid

import pytest

from src.backend.db.connection import get_connection
from src.backend.db.repository import get_business_config, get_user_by_email
from src.backend.tools.executor import execute_tool


@pytest.fixture(scope="module")
def customer_id() -> str:
    return get_user_by_email("demo.customer@gsm.vn")["id"]


@pytest.fixture
def conversation() -> str:
    """Một hội thoại dùng riêng cho test, xoá sạch sau khi xong."""
    cust = get_user_by_email("demo.customer@gsm.vn")["id"]
    thread = f"pytest-{uuid.uuid4().hex[:10]}"
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("INSERT INTO conversations (customer_id, thread_id) VALUES (%s,%s) RETURNING id",
                    (cust, thread))
        conv_id = str(cur.fetchone()[0])
    yield conv_id
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM refund_requests WHERE conversation_id = %s", (conv_id,))
        cur.execute("DELETE FROM tickets WHERE conversation_id = %s", (conv_id,))
        cur.execute("DELETE FROM tool_calls WHERE conversation_id = %s", (conv_id,))
        cur.execute("DELETE FROM conversations WHERE id = %s", (conv_id,))


def _cleanup_refunds(codes: list[str]) -> None:
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM audit_log WHERE entity_id = ANY(%s)", (codes,))
        cur.execute("DELETE FROM refund_requests WHERE refund_code = ANY(%s)", (codes,))


def _clear_month_approvals(customer_id: str) -> None:
    """Xoá các lần hoàn tiền ĐÃ DUYỆT trong tháng của khách demo.

    Hạn mức `refund.auto_approve_max_per_month` là quy tắc **có trạng thái tích
    luỹ** (KB 03 mục 4): từ lần thứ 3 trong tháng, mọi yêu cầu đều bị ép sang
    HITL dù số tiền nhỏ. Test nào muốn kiểm nhánh tự duyệt thì phải tự dọn trạng
    thái trước, nếu không kết quả phụ thuộc vào việc đã chạy bao nhiêu test khác.
    """
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            "DELETE FROM refund_requests WHERE customer_id = %s "
            "AND status IN ('AUTO_APPROVED','APPROVED') "
            "AND created_at >= date_trunc('month', now())", (customer_id,))


def _cleanup_rides(codes: list[str]) -> None:
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM rides WHERE ride_code = ANY(%s)", (codes,))


# ---------------------------------------------------------------------------
# Ngưỡng hoàn tiền — LLM không được quyết, business_config quyết (ADR-006)
# ---------------------------------------------------------------------------
def test_hoan_tien_duoi_nguong_thi_ai_tu_duyet(customer_id, conversation):
    _clear_month_approvals(customer_id)
    threshold = get_business_config()["refund.auto_approve_max_vnd"]
    result = execute_tool("request_refund", {
        "conversation_id": conversation, "customer_id": customer_id,
        "ride_code": "XSM-DOUBLE-01", "amount": threshold - 18_000,
        "reason_code": "DOUBLE_CHARGE", "reason_detail": "Bi tru tien hai lan cho cung mot chuyen",
    }, conversation_id=conversation)
    assert result.ok, result.error
    assert result.data.status == "AUTO_APPROVED"
    assert result.data.escalation_reason is None
    assert result.data.threshold_applied == threshold
    _cleanup_refunds([result.data.refund_code])


def test_hoan_tien_tren_nguong_thi_bat_buoc_chuyen_nguoi_duyet(customer_id, conversation):
    threshold = get_business_config()["refund.auto_approve_max_vnd"]
    result = execute_tool("request_refund", {
        "conversation_id": conversation, "customer_id": customer_id,
        "ride_code": "XSM-DOUBLE-02", "amount": threshold + 70_000,
        "reason_code": "DOUBLE_CHARGE", "reason_detail": "Bi tru tien hai lan, so tien lon",
    }, conversation_id=conversation)
    assert result.ok, result.error
    assert result.data.status == "PENDING_HITL"
    # Lý do phải nêu được con số, vì CSKH đọc nó để quyết định
    assert result.data.escalation_reason and str(threshold)[:2] in result.data.escalation_reason
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("SELECT status, decided_at, resume_thread_id FROM refund_requests "
                    "WHERE refund_code = %s", (result.data.refund_code,))
        status, decided_at, resume = cur.fetchone()
    assert status == "PENDING_HITL"
    assert decided_at is None, "Chưa ai duyệt thì không được có thời điểm quyết định"
    assert resume == conversation, "Phải lưu thread để T-011 đánh thức lại graph"
    _cleanup_refunds([result.data.refund_code])


def test_khong_hoan_tien_cho_chuyen_cua_nguoi_khac(conversation):
    """Và thông báo không được để lộ rằng chuyến đó tồn tại nhưng thuộc người khác."""
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("SELECT id FROM users WHERE email = 'customer01@gsm.vn'")
        other_id = str(cur.fetchone()[0])
    result = execute_tool("request_refund", {
        "conversation_id": conversation, "customer_id": other_id,
        "ride_code": "XSM-DOUBLE-02", "amount": 20_000,
        "reason_code": "DOUBLE_CHARGE", "reason_detail": "Thu chiem doat chuyen cua nguoi khac",
    }, conversation_id=conversation)
    assert not result.ok
    assert result.error.code == "RIDE_NOT_FOUND"
    assert "người khác" not in result.error.message_for_user


# ---------------------------------------------------------------------------
# Chống gọi trùng (ADR-005) — tầng bảo vệ không phụ thuộc vào LLM
# ---------------------------------------------------------------------------
def test_goi_lai_cung_yeu_cau_khong_hoan_tien_hai_lan(customer_id, conversation):
    payload = {
        "conversation_id": conversation, "customer_id": customer_id,
        "ride_code": "XSM-FAREDIFF-01", "amount": 42_000,
        "reason_code": "FARE_DISCREPANCY", "reason_detail": "Bao gia 85k nhung tru 127k",
    }
    first = execute_tool("request_refund", payload, conversation_id=conversation)
    second = execute_tool("request_refund", payload, conversation_id=conversation)

    assert first.ok and second.ok
    assert not first.replayed, "Lần đầu phải thực thi thật"
    assert second.replayed, "Lần hai phải trả kết quả cũ, không thực thi lại"
    assert first.data.refund_code == second.data.refund_code

    with get_connection() as conn, conn.cursor() as cur:
        # T-011 gan refund vao conversation de dashboard join duoc; truoc do cot nay de NULL
        cur.execute("SELECT count(*) FROM refund_requests WHERE resume_thread_id = %s",
                    (conversation,))
        count = cur.fetchone()[0]
    assert count == 1, f"Phải chỉ có đúng 1 yêu cầu hoàn tiền, đang có {count}"
    _cleanup_refunds([first.data.refund_code])


def test_dat_xe_hai_lan_chi_tao_mot_chuyen(customer_id, conversation):
    payload = {
        "conversation_id": conversation, "customer_id": customer_id,
        "pickup_address": "12 Nguyen Trai, Thanh Xuan, Ha Noi",
        "dropoff_address": "45 Kim Ma, Ba Dinh, Ha Noi",
        "service_type": "BIKE", "payment_method": "CASH",
    }
    first = execute_tool("book_ride", payload, conversation_id=conversation)
    second = execute_tool("book_ride", payload, conversation_id=conversation)
    assert first.ok and second.ok
    assert second.replayed
    assert first.data.ride_code == second.data.ride_code
    _cleanup_rides([first.data.ride_code])


# ---------------------------------------------------------------------------
# Phí huỷ — tính theo cửa sổ miễn phí trong business_config
# ---------------------------------------------------------------------------
def test_huy_ngay_sau_khi_dat_thi_mien_phi(customer_id, conversation):
    booked = execute_tool("book_ride", {
        "conversation_id": conversation, "customer_id": customer_id,
        "pickup_address": "1 Trang Tien, Hoan Kiem, Ha Noi",
        "dropoff_address": "9 Lang Ha, Dong Da, Ha Noi", "service_type": "GREENCAR",
    }, conversation_id=conversation)
    assert booked.ok

    cancelled = execute_tool("cancel_ride", {
        "conversation_id": conversation, "ride_code": booked.data.ride_code,
        "reason": "Khach doi y",
    }, conversation_id=conversation)
    assert cancelled.ok, cancelled.error
    assert cancelled.data.cancel_fee == 0
    assert cancelled.data.fee_waived is True
    # Lời giải thích là thứ khách đọc khi khiếu nại — bắt buộc phải có căn cứ
    assert "miễn phí" in cancelled.data.fee_explanation
    _cleanup_rides([booked.data.ride_code])


def test_huy_chuyen_da_huy_thi_bao_loi_ro_rang(conversation):
    result = execute_tool("cancel_ride", {
        "conversation_id": conversation, "ride_code": "XSM-CANCELFEE-01",
        "reason": "Thu huy lan nua",
    }, conversation_id=conversation)
    assert not result.ok
    assert result.error.code == "ALREADY_CANCELLED"
    assert result.error.error_type.value == "FATAL", "Không được thử lại lỗi kiểu này"


def test_khong_huy_duoc_chuyen_da_hoan_thanh(conversation):
    result = execute_tool("cancel_ride", {
        "conversation_id": conversation, "ride_code": "XSM-LOSTITEM-01",
        "reason": "Thu huy chuyen da xong",
    }, conversation_id=conversation)
    assert not result.ok
    assert result.error.code == "ALREADY_COMPLETED"


# ---------------------------------------------------------------------------
# Tool đọc
# ---------------------------------------------------------------------------
def test_uoc_tinh_cuoc_tach_bach_tung_khoan(conversation):
    result = execute_tool("estimate_fare", {
        "conversation_id": conversation, "pickup_address": "A", "dropoff_address": "B",
        "service_type": "BIKE", "distance_km": 6.0,
    }, conversation_id=conversation)
    assert result.ok
    cfg = get_business_config()
    data = result.data
    assert data.base_fare == cfg["fare.bike_base_vnd"]
    # 6km - 2km miễn phí đầu = 4km tính tiền
    assert data.distance_fare == 4 * cfg["fare.bike_per_km_vnd"]
    assert data.total_fare >= data.base_fare + data.distance_fare - 500


def test_chi_tiet_chuyen_tinh_dung_phan_tram_di_vong(conversation):
    result = execute_tool("get_ride_detail", {
        "conversation_id": conversation, "ride_code": "XSM-DETOUR-01",
    }, conversation_id=conversation)
    assert result.ok
    assert result.data.deviation_pct == 61.5
    assert any(e.event_type == "ROUTE_DEVIATION" for e in result.data.events)


def test_lich_su_chuyen_tra_dung_khach(customer_id, conversation):
    result = execute_tool("get_ride_history", {
        "conversation_id": conversation, "customer_id": customer_id,
        "limit": 5, "since_days": 365,
    }, conversation_id=conversation)
    assert result.ok
    assert len(result.data.rides) <= 5
    assert result.data.total_found >= 11  # 11 case khó đều thuộc khách demo


# ---------------------------------------------------------------------------
# Phân loại lỗi
# ---------------------------------------------------------------------------
def test_tool_khong_ton_tai(conversation):
    result = execute_tool("xoa_toan_bo_du_lieu", {}, conversation_id=conversation)
    assert not result.ok
    assert result.error.code == "UNKNOWN_TOOL"


def test_thieu_tham_so_bat_buoc_bao_FATAL(customer_id, conversation):
    result = execute_tool("create_ticket", {
        "conversation_id": conversation, "customer_id": customer_id,
        "category": "LOST_ITEM", "description": "Quen do tren xe",
    }, conversation_id=conversation)
    assert not result.ok
    assert result.error.code == "INVALID_ARGUMENTS"
    assert result.error.error_type.value == "FATAL"
    # Thông báo cho khách không được lộ chi tiết kỹ thuật
    assert "ValidationError" not in result.error.message_for_user
    assert "ride_code" not in result.error.message_for_user


def test_moi_loi_goi_tool_sinh_dung_mot_dong_log(customer_id, conversation):
    execute_tool("estimate_fare", {
        "conversation_id": conversation, "pickup_address": "A", "dropoff_address": "B",
        "service_type": "LUXURY", "distance_km": 3.0,
    }, conversation_id=conversation)
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM tool_calls WHERE conversation_id = %s "
                    "AND tool_name = 'estimate_fare'", (conversation,))
        assert cur.fetchone()[0] == 1


def test_vuot_han_muc_thang_thi_ep_sang_HITL_du_so_tien_nho(customer_id, conversation):
    """Quy tắc chống gian lận của KB 03 mục 4, kiểm bằng cách chạy đủ 3 lần.

    Test này ra đời từ một lần báo đỏ tưởng là lỗi: khách demo đã có 2 lần hoàn
    tiền được duyệt trong tháng nên lần thứ 3 bị ép sang HITL — đúng quy tắc, chỉ
    là chưa có ai kiểm nó một cách tường minh.
    """
    _clear_month_approvals(customer_id)
    threshold = get_business_config()["refund.auto_approve_max_vnd"]
    cap = get_business_config()["refund.auto_approve_max_per_month"]
    small = threshold - 20_000
    codes: list[str] = []

    statuses = []
    for index in range(cap + 1):
        result = execute_tool("request_refund", {
            "conversation_id": conversation, "customer_id": customer_id,
            "ride_code": "XSM-DOUBLE-01", "amount": small - index,  # đổi số để khác idem key
            "reason_code": "DOUBLE_CHARGE", "reason_detail": f"Lan thu {index + 1} trong thang",
        }, conversation_id=conversation)
        assert result.ok, result.error
        statuses.append(result.data.status)
        codes.append(result.data.refund_code)

    assert statuses[:cap] == ["AUTO_APPROVED"] * cap, statuses
    assert statuses[cap] == "PENDING_HITL", (
        f"Lần thứ {cap + 1} trong tháng phải chuyển người duyệt dù số tiền nhỏ, "
        f"nhưng nhận {statuses[cap]}"
    )
    _cleanup_refunds(codes)
    _clear_month_approvals(customer_id)
