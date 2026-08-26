"""Thực thi 8 tool nghiệp vụ.

Ba điều lớp này bảo đảm, không phụ thuộc vào việc LLM cư xử đúng:

1. **Xác thực đầu vào bằng Pydantic.** LLM bịa tham số hoặc thiếu trường bắt buộc
   thì hỏng ngay ở đây với lỗi `FATAL`, chứ không lọt xuống tầng DB.
2. **Chống gọi trùng bằng `idempotency_key`** (ADR-005). Lần gọi thứ hai cùng nội
   dung không thực thi lại — nó trả về kết quả đã lưu, kèm cờ `replayed=True`.
3. **Ngưỡng nghiệp vụ đọc từ `business_config`** (ADR-006), không hardcode.
   LLM không được quyền quyết định có tự duyệt hoàn tiền hay không — tầng này quyết.
4. **PII được token hoá trước khi rời khỏi lớp này** (ADR-004). Bảng `tool_calls`
   vẫn lưu giá trị THẬT cho CSKH truy vết — họ có quyền xem; còn thứ trả về cho
   graph, và từ đó đi vào context của LLM, chỉ chứa placeholder.
"""
from __future__ import annotations

import json
import random
import time
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ValidationError

from src.backend.db.connection import get_connection
from src.backend.db.repository import get_business_config, log_tool_call
from src.backend.pii.tokenizer import get_vault, tokenize_model
from src.backend.tools.contracts import (
    TOOL_REGISTRY,
    BookRideInput,
    BookRideOutput,
    CancelRideInput,
    CancelRideOutput,
    CreateTicketInput,
    CreateTicketOutput,
    EstimateFareInput,
    FareBreakdown,
    GetRideDetailInput,
    GetRideDetailOutput,
    GetRideHistoryInput,
    GetRideHistoryOutput,
    ModifyRideInput,
    ModifyRideOutput,
    RequestRefundInput,
    RequestRefundOutput,
    RideEvent,
    RideSummary,
    ToolError,
    ToolErrorType,
    ToolResult,
    WriteToolInput,
)

SERVICE_KEY = {"BIKE": "bike", "GREENCAR": "greencar", "LUXURY": "luxury"}
CANCEL_FEE_KEY = {"BIKE": "cancel.fee_bike_vnd", "GREENCAR": "cancel.fee_greencar_vnd",
                  "LUXURY": "cancel.fee_luxury_vnd"}
SLA_HOURS = {"LOW": 72, "NORMAL": 24, "HIGH": 8, "CRITICAL": 4}


class ToolExecutionError(Exception):
    """Lỗi nghiệp vụ đã được phân loại — nơi gọi biết ngay phải làm gì tiếp."""

    def __init__(self, error_type: ToolErrorType, code: str, message_for_user: str,
                 detail: str | None = None) -> None:
        super().__init__(message_for_user)
        self.error = ToolError(error_type=error_type, code=code,
                               message_for_user=message_for_user, detail_for_log=detail)


def _fatal(code: str, message: str) -> ToolExecutionError:
    return ToolExecutionError(ToolErrorType.FATAL, code, message)


def _new_code(prefix: str) -> str:
    return f"{prefix}-{datetime.now(UTC).strftime('%y%m%d')}-{random.randint(1000, 9999)}"


def _fetch_ride(cur: Any, ride_code: str) -> tuple:
    cur.execute(
        "SELECT r.id, r.ride_code, r.customer_id, r.driver_id, r.service_type, r.status, "
        "r.pickup_address, r.dropoff_address, r.planned_distance_km, r.actual_distance_km, "
        "r.quoted_fare, r.final_fare, r.cancel_fee, r.requested_at, r.started_at, "
        "r.completed_at, r.cancelled_at, d.full_name "
        "FROM rides r LEFT JOIN drivers d ON d.id = r.driver_id WHERE r.ride_code = %s",
        (ride_code,))
    row = cur.fetchone()
    if not row:
        raise _fatal("RIDE_NOT_FOUND",
                     f"Em không tìm thấy chuyến có mã {ride_code} trong hệ thống. "
                     "Anh/chị kiểm tra lại giúp em mã chuyến ạ.")
    return row


# ===========================================================================
# Tool chỉ đọc
# ===========================================================================
def _get_ride_history(inp: GetRideHistoryInput) -> GetRideHistoryOutput:
    sql = ("SELECT ride_code, service_type, status, pickup_address, dropoff_address, "
           "final_fare, requested_at FROM rides WHERE customer_id = %s "
           "AND requested_at >= now() - make_interval(days => %s)")
    params: list[Any] = [inp.customer_id, inp.since_days]
    if inp.status_filter:
        sql += " AND status = ANY(%s)"
        params.append(list(inp.status_filter))
    sql += " ORDER BY requested_at DESC LIMIT %s"
    params.append(inp.limit)

    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(sql, params)
        rows = cur.fetchall()
        cur.execute("SELECT count(*) FROM rides WHERE customer_id = %s", (inp.customer_id,))
        total = cur.fetchone()[0]
    return GetRideHistoryOutput(
        rides=[RideSummary(ride_code=r[0], service_type=r[1], status=r[2], pickup_address=r[3],
                           dropoff_address=r[4], final_fare=r[5], requested_at=r[6]) for r in rows],
        total_found=total,
    )


def _get_ride_detail(inp: GetRideDetailInput) -> GetRideDetailOutput:
    with get_connection() as conn, conn.cursor() as cur:
        r = _fetch_ride(cur, inp.ride_code)
        cur.execute("SELECT event_type, payload, created_at FROM ride_events "
                    "WHERE ride_id = %s ORDER BY created_at", (r[0],))
        events = [RideEvent(event_type=e[0], payload=e[1] or {}, created_at=e[2])
                  for e in cur.fetchall()]
        cur.execute("SELECT amount, method, status, transaction_ref, charged_at FROM payments "
                    "WHERE ride_id = %s ORDER BY charged_at", (r[0],))
        payments = [{"amount": p[0], "method": p[1], "status": p[2],
                     "transaction_ref": p[3], "charged_at": p[4]} for p in cur.fetchall()]
    return GetRideDetailOutput(
        ride_code=r[1], service_type=r[4], status=r[5], pickup_address=r[6], dropoff_address=r[7],
        final_fare=r[11], requested_at=r[13], driver_name=r[17], planned_distance_km=r[8],
        actual_distance_km=r[9], quoted_fare=r[10], cancel_fee=r[12], cancelled_at=r[16],
        completed_at=r[15], events=events, payments=payments,
    )


def _estimate_fare(inp: EstimateFareInput) -> FareBreakdown:
    cfg = get_business_config()
    key = SERVICE_KEY[inp.service_type]
    base = cfg[f"fare.{key}_base_vnd"]
    per_km = cfg[f"fare.{key}_per_km_vnd"]
    base_km = cfg["fare.base_distance_km"]

    # Không có quãng đường thì ước tính bằng con số trung bình nội thành, và nói rõ
    # trong phần ghi chú rằng đây chỉ là ước lượng.
    distance = inp.distance_km if inp.distance_km else 5.0
    distance_fare = round(max(0.0, distance - base_km) * per_km)

    when = inp.pickup_time or datetime.now(UTC)
    night_start, night_end = cfg["fare.night_start_hour"], cfg["fare.night_end_hour"]
    is_night = when.hour >= night_start or when.hour < night_end
    night = 0
    if is_night:
        night = (cfg["fare.night_surcharge_bike_vnd"] if inp.service_type == "BIKE"
                 else cfg["fare.night_surcharge_car_vnd"])

    stops = min(inp.extra_stops, cfg["fare.max_extra_stops"])
    stop_fee = stops * cfg["fare.extra_stop_vnd"]
    total = base + distance_fare + night + stop_fee
    return FareBreakdown(
        base_fare=base, distance_fare=int(distance_fare), night_surcharge=night,
        extra_stop_fee=stop_fee, total_fare=int(round(total / 500) * 500),
        policy_source="01_pricing_and_surcharges.md",
    )


# ===========================================================================
# Tool ghi dữ liệu
# ===========================================================================
def _book_ride(inp: BookRideInput, idem: str) -> BookRideOutput:
    cfg = get_business_config()
    key = SERVICE_KEY[inp.service_type]
    estimated = cfg[f"fare.{key}_base_vnd"] + round(3.0 * cfg[f"fare.{key}_per_km_vnd"])
    ride_code = _new_code("XSM")
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("SELECT id, full_name FROM drivers WHERE service_type = %s "
                    "ORDER BY random() LIMIT 1", (inp.service_type,))
        driver = cur.fetchone()
        cur.execute(
            "INSERT INTO rides (ride_code, customer_id, driver_id, service_type, status, "
            "pickup_address, dropoff_address, planned_distance_km, quoted_fare, "
            "payment_method, idempotency_key) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (ride_code, inp.customer_id, driver[0] if driver else None, inp.service_type,
             "ASSIGNED" if driver else "PENDING", inp.pickup_address, inp.dropoff_address,
             3.0, estimated, inp.payment_method, idem))
    return BookRideOutput(
        ride_code=ride_code, status="ASSIGNED" if driver else "PENDING",
        estimated_fare=int(estimated), driver_name=driver[1] if driver else None,
        eta_minutes=random.randint(3, 9) if driver else None,
    )


def _cancel_ride(inp: CancelRideInput, idem: str) -> CancelRideOutput:
    cfg = get_business_config()
    free_window = cfg["cancel.free_window_seconds"]
    now = datetime.now(UTC)
    with get_connection() as conn, conn.cursor() as cur:
        r = _fetch_ride(cur, inp.ride_code)
        status, service_type, requested_at = r[5], r[4], r[13]
        if status == "CANCELLED":
            raise _fatal("ALREADY_CANCELLED",
                         f"Chuyến {inp.ride_code} đã được huỷ trước đó rồi ạ.")
        if status == "COMPLETED":
            raise _fatal("ALREADY_COMPLETED",
                         f"Chuyến {inp.ride_code} đã hoàn thành nên không huỷ được nữa ạ.")

        elapsed = (now - requested_at).total_seconds()
        within_free = elapsed <= free_window
        fee = 0 if within_free else cfg[CANCEL_FEE_KEY[service_type]]
        if within_free:
            explanation = (f"Anh/chị huỷ trong {int(elapsed)} giây đầu, nằm trong cửa sổ miễn phí "
                           f"{free_window} giây nên không phát sinh phí huỷ ạ.")
        else:
            explanation = (f"Anh/chị huỷ sau {int(elapsed // 60)} phút kể từ lúc tài xế nhận chuyến, "
                           f"vượt cửa sổ miễn phí {free_window} giây, nên phát sinh phí huỷ "
                           f"{fee:,} VNĐ theo biểu phí dịch vụ.".replace(",", "."))

        cur.execute(
            "UPDATE rides SET status='CANCELLED', cancelled_at=%s, cancel_fee=%s, "
            "cancel_reason=%s, cancelled_by='CUSTOMER' WHERE id=%s",
            (now, fee, inp.reason[:300], r[0]))
        cur.execute("INSERT INTO ride_events (ride_id, event_type, payload) VALUES (%s,%s,%s::jsonb)",
                    (r[0], "CANCELLED",
                     json.dumps({"cancelled_after_seconds": int(elapsed), "fee": fee})))
    return CancelRideOutput(ride_code=inp.ride_code, cancelled_at=now, cancel_fee=fee,
                            fee_waived=within_free, fee_explanation=explanation)


def _modify_ride(inp: ModifyRideInput, idem: str) -> ModifyRideOutput:
    cfg = get_business_config()
    with get_connection() as conn, conn.cursor() as cur:
        r = _fetch_ride(cur, inp.ride_code)
        if r[5] not in ("ASSIGNED", "IN_PROGRESS"):
            raise _fatal("RIDE_NOT_ACTIVE",
                         f"Chuyến {inp.ride_code} đang ở trạng thái {r[5]} nên không đổi được ạ.")
        stop_fee = cfg["fare.extra_stop_vnd"] if inp.add_stop_address else 0
        delta = stop_fee
        if inp.new_dropoff_address:
            key = SERVICE_KEY[r[4]]
            delta += round(1.5 * cfg[f"fare.{key}_per_km_vnd"])  # ước lượng chênh quãng đường
        new_fare = int((r[10] or 0) + delta)
        if inp.new_dropoff_address:
            cur.execute("UPDATE rides SET dropoff_address=%s, quoted_fare=%s WHERE id=%s",
                        (inp.new_dropoff_address, new_fare, r[0]))
        else:
            cur.execute("UPDATE rides SET quoted_fare=%s WHERE id=%s", (new_fare, r[0]))
    return ModifyRideOutput(ride_code=inp.ride_code, new_dropoff_address=inp.new_dropoff_address,
                            fare_delta=int(delta), new_estimated_fare=new_fare,
                            extra_stop_fee=stop_fee)


def _create_ticket(inp: CreateTicketInput, idem: str) -> CreateTicketOutput:
    ticket_code = _new_code("TK")
    with get_connection() as conn, conn.cursor() as cur:
        ride_id = None
        if inp.ride_code:
            ride_id = _fetch_ride(cur, inp.ride_code)[0]
        cur.execute(
            "INSERT INTO tickets (ticket_code, customer_id, ride_id, category, severity, "
            "description, idempotency_key) VALUES (%s,%s,%s,%s,%s,%s,%s)",
            (ticket_code, inp.customer_id, ride_id, inp.category.value, inp.severity,
             inp.description, idem))
        cur.execute(
            "INSERT INTO audit_log (actor_type, action, entity_type, entity_id, reason) "
            "VALUES ('AI_AGENT','TICKET_CREATED','tickets',%s,%s)",
            (ticket_code, f"Khiếu nại loại {inp.category.value}"))
    return CreateTicketOutput(ticket_code=ticket_code, category=inp.category,
                              severity=inp.severity, status="OPEN",
                              sla_hours=SLA_HOURS[inp.severity])


def _request_refund(inp: RequestRefundInput, idem: str) -> RequestRefundOutput:
    """LLM KHÔNG được quyết có duyệt hay không. Hàm này quyết, dựa trên business_config."""
    cfg = get_business_config()
    threshold = cfg["refund.auto_approve_max_vnd"]
    max_per_month = cfg["refund.auto_approve_max_per_month"]
    fraud_ceiling = cfg["refund.fraud_score_hitl_threshold"]
    refund_code = _new_code("RF")
    now = datetime.now(UTC)

    with get_connection() as conn, conn.cursor() as cur:
        ride = _fetch_ride(cur, inp.ride_code)
        if str(ride[2]) != inp.customer_id:
            # Không tiết lộ rằng chuyến này thuộc về người khác — chỉ nói không tìm thấy.
            raise _fatal("RIDE_NOT_FOUND",
                         f"Em không tìm thấy chuyến {inp.ride_code} trong lịch sử của anh/chị ạ.")

        cur.execute(
            "SELECT count(*) FROM refund_requests WHERE customer_id = %s "
            "AND status IN ('AUTO_APPROVED','APPROVED') "
            "AND created_at >= date_trunc('month', now())", (inp.customer_id,))
        approved_this_month = cur.fetchone()[0]

        fraud_score = min(1.0, approved_this_month * 0.25)
        reasons: list[str] = []
        if inp.amount > threshold:
            reasons.append(f"Số tiền {inp.amount:,} VNĐ vượt ngưỡng tự duyệt {threshold:,} VNĐ"
                           .replace(",", "."))
        if approved_this_month >= max_per_month:
            reasons.append(f"Đã có {approved_this_month} lần hoàn tiền được duyệt trong tháng, "
                           f"vượt hạn mức {max_per_month} lần")
        if fraud_score > fraud_ceiling:
            reasons.append(f"Điểm nghi ngờ gian lận {fraud_score:.2f} vượt ngưỡng {fraud_ceiling}")

        needs_human = bool(reasons)
        status = "PENDING_HITL" if needs_human else "AUTO_APPROVED"
        cur.execute(
            "INSERT INTO refund_requests (refund_code, customer_id, ride_id, conversation_id, "
            "amount, reason_code, reason_detail, fraud_score, status, resume_thread_id, "
            "idempotency_key, decided_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (refund_code, inp.customer_id, ride[0], inp.conversation_id, inp.amount,
             inp.reason_code.value,
             inp.reason_detail, fraud_score, status, inp.conversation_id, idem,
             None if needs_human else now))
        cur.execute(
            "INSERT INTO audit_log (actor_type, action, entity_type, entity_id, reason) "
            "VALUES ('AI_AGENT',%s,'refund_requests',%s,%s)",
            ("REFUND_ESCALATED" if needs_human else "REFUND_AUTO_APPROVED", refund_code,
             " · ".join(reasons) if reasons else
             f"Số tiền {inp.amount} VNĐ trong ngưỡng tự duyệt {threshold} VNĐ"))

    return RequestRefundOutput(
        refund_code=refund_code, amount=inp.amount, status=status, threshold_applied=threshold,
        escalation_reason=" · ".join(reasons) if reasons else None,
        estimated_completion=("trong vòng 04 giờ làm việc sau khi được duyệt" if needs_human
                              else "trong vòng 05 phút"),
    )


# ===========================================================================
# Điều phối
# ===========================================================================
_IMPL = {
    "get_ride_history": _get_ride_history,
    "get_ride_detail": _get_ride_detail,
    "estimate_fare": _estimate_fare,
    "book_ride": _book_ride,
    "cancel_ride": _cancel_ride,
    "modify_ride": _modify_ride,
    "create_ticket": _create_ticket,
    "request_refund": _request_refund,
}


def _replayed_result(idem: str) -> dict | None:
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("SELECT result FROM tool_calls WHERE idempotency_key = %s "
                    "AND status = 'SUCCESS' LIMIT 1", (idem,))
        row = cur.fetchone()
    return row[0] if row else None


def execute_tool(tool_name: str, payload: dict[str, Any], *,
                 conversation_id: str | None = None) -> ToolResult:
    """Điểm vào duy nhất để gọi bất kỳ tool nào. Graph chỉ được gọi qua đây."""
    started = time.perf_counter()
    spec = TOOL_REGISTRY.get(tool_name)
    if spec is None:
        return ToolResult(ok=False, error=ToolError(
            error_type=ToolErrorType.FATAL, code="UNKNOWN_TOOL",
            message_for_user="Em chưa hỗ trợ thao tác này ạ.",
            detail_for_log=f"tool không tồn tại: {tool_name}"))

    # 1. Xác thực đầu vào — LLM bịa tham số thì hỏng ở đây
    try:
        parsed = spec.input_model(**payload)
    except ValidationError as exc:
        error = ToolError(
            error_type=ToolErrorType.FATAL, code="INVALID_ARGUMENTS",
            message_for_user="Em còn thiếu thông tin để xử lý yêu cầu này. "
                             "Anh/chị bổ sung giúp em ạ.",
            detail_for_log=exc.json()[:1000])
        log_tool_call(conversation_id, tool_name, payload, status="ERROR",
                      error_type=error.error_type.value, error_message=error.detail_for_log,
                      latency_ms=int((time.perf_counter() - started) * 1000))
        return ToolResult(ok=False, error=error)

    # 2. Chống gọi trùng (ADR-005)
    idem: str | None = None
    if spec.writes_data and isinstance(parsed, WriteToolInput):
        idem = parsed.idempotency_key or parsed.build_idempotency_key(tool_name)
        cached = _replayed_result(idem)
        if cached is not None:
            restored = spec.output_model(**cached)
            return ToolResult(
                ok=True,
                data=tokenize_model(restored, get_vault(conversation_id)),
                replayed=True,
                latency_ms=int((time.perf_counter() - started) * 1000))

    # 3. Thực thi
    try:
        impl = _IMPL[tool_name]
        output: BaseModel = impl(parsed, idem) if spec.writes_data else impl(parsed)
    except ToolExecutionError as exc:
        log_tool_call(conversation_id, tool_name, payload, status="ERROR",
                      error_type=exc.error.error_type.value,
                      error_message=exc.error.detail_for_log or exc.error.code,
                      idempotency_key=None,
                      latency_ms=int((time.perf_counter() - started) * 1000))
        return ToolResult(ok=False, error=exc.error)
    except Exception as exc:  # noqa: BLE001 — hạ tầng hỏng, coi là thử lại được
        error = ToolError(
            error_type=ToolErrorType.RETRYABLE, code="INFRASTRUCTURE_ERROR",
            message_for_user="Hệ thống đang bận, anh/chị chờ em thử lại giúp ạ.",
            detail_for_log=f"{type(exc).__name__}: {exc}"[:1000])
        log_tool_call(conversation_id, tool_name, payload, status="ERROR",
                      error_type=error.error_type.value, error_message=error.detail_for_log,
                      latency_ms=int((time.perf_counter() - started) * 1000))
        return ToolResult(ok=False, error=error)

    latency_ms = int((time.perf_counter() - started) * 1000)
    # Ghi giá trị THẬT vào tool_calls: CSKH có quyền xem, và tool trace mất PII thì
    # không xử lý được ca. Chỉ bản trả về cho graph mới bị token hoá.
    result_json = json.loads(output.model_dump_json())
    logged = log_tool_call(conversation_id, tool_name, payload, result=result_json,
                           idempotency_key=idem, latency_ms=latency_ms)
    output = tokenize_model(output, get_vault(conversation_id))
    # `logged is None` nghĩa là ràng buộc UNIQUE ở DB vừa chặn một lời gọi trùng mà
    # bước kiểm ở trên chưa kịp thấy (hai lượt chạy song song). Vẫn coi là thành công,
    # nhưng đánh dấu replayed để tầng trên không báo với khách hai lần.
    return ToolResult(ok=True, data=output, replayed=logged is None, latency_ms=latency_ms)


# ===========================================================================
# Suy ra quyền được hoàn tiền từ BẰNG CHỨNG, không từ lời khai của khách
# ===========================================================================
def derive_refund_evidence(ride_code: str) -> dict[str, Any] | None:
    """Đối soát dữ liệu chuyến để xác định khách có thực sự được hoàn tiền không.

    Vì sao không dùng con số khách tự nói: (1) khách thường không biết mình được
    hoàn bao nhiêu, (2) để khách tự khai số tiền là mở đường cho gian lận, (3) mỗi
    lý do hoàn tiền có cách tính riêng đã ghi trong `data/knowledge_base/03_*`.

    Trả về None khi **không đủ điều kiện** — đó là kết quả hợp lệ và quan trọng
    không kém: agent phải biết từ chối đúng, chứ không chỉ biết đồng ý đúng.
    """
    cfg = get_business_config()
    with get_connection() as conn, conn.cursor() as cur:
        r = _fetch_ride(cur, ride_code)
        ride_id, service_type, status = r[0], r[4], r[5]
        planned, actual = r[8], r[9]
        quoted, final, cancel_fee = r[10], r[11], r[12]
        requested_at, cancelled_at = r[13], r[16]

        cur.execute("SELECT amount, charged_at FROM payments WHERE ride_id = %s "
                    "AND status = 'SUCCESS' ORDER BY charged_at", (ride_id,))
        payments = cur.fetchall()

        cur.execute("SELECT event_type FROM ride_events WHERE ride_id = %s", (ride_id,))
        events = {e[0] for e in cur.fetchall()}

    # 1. Thu tiền trùng — bằng chứng mạnh nhất: hai giao dịch SUCCESS cùng chuyến
    if len(payments) > 1:
        amount = min(int(p[0]) for p in payments)
        return {"reason_code": "DOUBLE_CHARGE", "amount": amount,
                "evidence": f"Hệ thống ghi nhận {len(payments)} giao dịch thành công cho cùng "
                            f"chuyến {ride_code}. Hoàn lại khoản bị trừ thừa {amount:,} VNĐ."
                            .replace(",", ".")}

    # 2. Phí huỷ thu sai — huỷ trong cửa sổ miễn phí mà vẫn bị tính
    if status == "CANCELLED" and cancel_fee and cancelled_at and requested_at:
        elapsed = (cancelled_at - requested_at).total_seconds()
        window = cfg["cancel.free_window_seconds"]
        if elapsed <= window:
            return {"reason_code": "WRONG_CANCEL_FEE", "amount": int(cancel_fee),
                    "evidence": f"Chuyến bị huỷ sau {int(elapsed)} giây, nằm trong cửa sổ miễn "
                                f"phí {window} giây, nhưng vẫn bị thu {cancel_fee:,} VNĐ."
                                .replace(",", ".")}

    # 3. Đi vòng vượt ngưỡng — chỉ hoàn phần cước của quãng đường dôi ra
    if planned and actual:
        deviation = (float(actual) / float(planned) - 1) * 100
        threshold_pct = cfg["route.deviation_threshold_pct"]
        if deviation > threshold_pct:
            per_km = cfg[f"fare.{SERVICE_KEY[service_type]}_per_km_vnd"]
            excess_km = float(actual) - float(planned)
            amount = int(round(excess_km * per_km / 500) * 500)
            return {"reason_code": "ROUTE_INEFFICIENCY", "amount": amount,
                    "evidence": f"Quãng đường thực tế {actual} km so với lộ trình chuẩn "
                                f"{planned} km, vượt {deviation:.1f}% (ngưỡng {threshold_pct}%). "
                                f"Hoàn phần cước của {excess_km:.1f} km dôi ra."}

    # 4. Chênh lệch cước so với giá đã báo lúc đặt
    if quoted and final and final > quoted:
        diff = int(final) - int(quoted)
        if diff > 0 and diff / quoted > 0.1:
            return {"reason_code": "FARE_DISCREPANCY", "amount": diff,
                    "evidence": f"Giá hiển thị lúc đặt là {quoted:,} VNĐ nhưng thực tế bị trừ "
                                f"{final:,} VNĐ, chênh {diff:,} VNĐ.".replace(",", ".")}

    # 5. Gián đoạn giữa đường
    if "VEHICLE_ISSUE" in events and final:
        amount = int(round(int(final) * 0.5 / 500) * 500)
        return {"reason_code": "SERVICE_INTERRUPTION", "amount": amount,
                "evidence": f"Chuyến bị gián đoạn do sự cố phương tiện. "
                            f"Hoàn 50% cước, tương đương {amount:,} VNĐ.".replace(",", ".")}

    return None
