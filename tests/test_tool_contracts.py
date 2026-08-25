"""Kiểm thử hợp đồng tool — chạy: .venv/Scripts/python -m pytest"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.backend.tools.contracts import (
    READ_TOOLS,
    TOOL_REGISTRY,
    WRITE_TOOLS,
    BookRideInput,
    CreateTicketInput,
    GetRideDetailOutput,
    ModifyRideInput,
    RequestRefundInput,
    TicketCategory,
    ToolErrorType,
    pii_fields_of,
)


def test_moi_tool_ghi_du_lieu_deu_sinh_duoc_idempotency_key():
    """ADR-005: không tool ghi nào được phép thiếu cơ chế chống gọi trùng."""
    for name in WRITE_TOOLS:
        assert hasattr(TOOL_REGISTRY[name].input_model, "build_idempotency_key"), name


def test_cung_yeu_cau_cho_ra_cung_key_khac_yeu_cau_cho_ra_khac_key():
    a = BookRideInput(conversation_id="c1", customer_id="u1", pickup_address="12 Nguyễn Trãi",
                      dropoff_address="45 Kim Mã", service_type="BIKE")
    b = BookRideInput(conversation_id="c1", customer_id="u1", pickup_address="12 Nguyễn Trãi",
                      dropoff_address="45 Kim Mã", service_type="BIKE")
    c = BookRideInput(conversation_id="c1", customer_id="u1", pickup_address="12 Nguyễn Trãi",
                      dropoff_address="99 Láng Hạ", service_type="BIKE")
    d = BookRideInput(conversation_id="c2", customer_id="u1", pickup_address="12 Nguyễn Trãi",
                      dropoff_address="45 Kim Mã", service_type="BIKE")
    assert a.build_idempotency_key("book_ride") == b.build_idempotency_key("book_ride")
    assert a.build_idempotency_key("book_ride") != c.build_idempotency_key("book_ride")
    # hội thoại khác nhau không được chặn nhầm lẫn nhau
    assert a.build_idempotency_key("book_ride") != d.build_idempotency_key("book_ride")


def test_ma_chuyen_sai_dinh_dang_bi_chan():
    with pytest.raises(ValidationError):
        RequestRefundInput(conversation_id="c1", customer_id="u1", ride_code="linh-tinh",
                           amount=50_000, reason_code="DOUBLE_CHARGE", reason_detail="bi tru 2 lan")


def test_so_tien_hoan_phai_duong():
    with pytest.raises(ValidationError):
        RequestRefundInput(conversation_id="c1", customer_id="u1", ride_code="XSM-DOUBLE-01",
                           amount=0, reason_code="DOUBLE_CHARGE", reason_detail="bi tru 2 lan")


def test_khieu_nai_that_lac_do_bat_buoc_co_ma_chuyen():
    """Agent không được tạo ticket mò khi chưa biết chuyến nào."""
    with pytest.raises(ValidationError):
        CreateTicketInput(conversation_id="c1", customer_id="u1",
                          category=TicketCategory.LOST_ITEM, description="quen tui tren xe")
    ok = CreateTicketInput(conversation_id="c1", customer_id="u1",
                           category=TicketCategory.LOST_ITEM, description="quen tui tren xe",
                           ride_code="XSM-LOSTITEM-01")
    assert ok.ride_code == "XSM-LOSTITEM-01"


def test_modify_ride_phai_co_it_nhat_mot_thay_doi():
    with pytest.raises(ValidationError):
        ModifyRideInput(conversation_id="c1", ride_code="XSM-ACTIVE-01")


def test_tool_khong_nhan_tham_so_la():
    """extra='forbid' — LLM bịa thêm tham số thì phải fail sớm, không âm thầm bỏ qua."""
    with pytest.raises(ValidationError):
        BookRideInput(conversation_id="c1", customer_id="u1", pickup_address="a b c",
                      dropoff_address="d e f", service_type="BIKE", auto_approve=True)


def test_truong_pii_duoc_danh_dau_day_du():
    """ADR-004: tokenizer dựa vào nhãn này, thiếu nhãn = lọt PII vào LLM."""
    assert set(pii_fields_of(GetRideDetailOutput)) >= {
        "pickup_address", "dropoff_address", "driver_name"}


def test_deviation_pct_tinh_dung():
    r = GetRideDetailOutput(ride_code="XSM-DETOUR-01", service_type="GREENCAR", status="COMPLETED",
                            pickup_address="a", dropoff_address="b",
                            requested_at="2026-08-25T10:00:00Z",
                            planned_distance_km=5.2, actual_distance_km=8.4)
    assert r.deviation_pct == 61.5


def test_phan_loai_loi_du_ba_nhanh():
    assert {e.value for e in ToolErrorType} == {"RETRYABLE", "FATAL", "NEEDS_HUMAN"}


def test_registry_phu_het_10_intent():
    """Mọi intent cần tool đều phải có ít nhất một tool phục vụ."""
    need_tools = {"booking.create", "booking.cancel", "booking.modify", "trip.lookup",
                  "fare.inquiry", "refund.request", "complaint.driver", "complaint.lost_item"}
    covered = {i for spec in TOOL_REGISTRY.values() for i in spec.intents}
    assert need_tools <= covered, need_tools - covered
    assert len(TOOL_REGISTRY) == 8
    assert len(WRITE_TOOLS) == 5 and len(READ_TOOLS) == 3
