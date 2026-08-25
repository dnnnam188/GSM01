"""Hợp đồng dữ liệu (Pydantic) cho toàn bộ tool nghiệp vụ của GSM-01.

Ba nguyên tắc chi phối file này:

1. **Output của tool là thứ đi thẳng vào context của LLM.** Vì vậy không một
   trường output nào được chứa PII thô — chỉ chứa placeholder do
   `pii/tokenizer` sinh ra (ADR-004). Trường nào là PII được đánh dấu bằng
   `pii=True` trong `json_schema_extra` để tokenizer biết đường xử lý.

2. **Mọi tool có ghi dữ liệu đều mang `idempotency_key`** (ADR-005). Key được
   sinh xác định từ nội dung yêu cầu, nên LLM gọi lại lần hai sẽ trùng key và
   bị tầng DB chặn thay vì thực thi hai lần.

3. **Lỗi được phân loại, không phải chuỗi tự do.** `ToolErrorType` quyết định
   graph làm gì tiếp: thử lại, bỏ cuộc, hay chuyển người thật.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime
from enum import StrEnum
from typing import Annotated, Any, Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field, model_validator

T = TypeVar("T")

RIDE_CODE_PATTERN = r"^XSM-[A-Z0-9\-]{3,20}$"
ServiceType = Literal["BIKE", "GREENCAR", "LUXURY"]


def pii_field(description: str, **kwargs: Any) -> Any:
    """Trường chứa PII — tokenizer phải thay bằng placeholder trước khi vào LLM."""
    return Field(description=description, json_schema_extra={"pii": True}, **kwargs)


# ===========================================================================
# Phân loại lỗi — quyết định hành vi của graph
# ===========================================================================
class ToolErrorType(StrEnum):
    """Lỗi thuộc loại nào quyết định graph xử lý ra sao.

    RETRYABLE   — lỗi tạm thời (timeout, 429, mất kết nối DB).
                  Graph thử lại tối đa `max_attempts`, có backoff.
    FATAL       — yêu cầu sai về bản chất (chuyến không tồn tại, đã huỷ rồi).
                  Không thử lại. Agent giải thích cho khách bằng lời.
    NEEDS_HUMAN — vượt thẩm quyền của AI (quá ngưỡng tiền, nghi gian lận).
                  Graph gọi interrupt() và chờ CSKH (ADR-003).
    """

    RETRYABLE = "RETRYABLE"
    FATAL = "FATAL"
    NEEDS_HUMAN = "NEEDS_HUMAN"


class ToolError(BaseModel):
    model_config = ConfigDict(frozen=True)

    error_type: ToolErrorType
    code: str = Field(description="Mã lỗi ngắn, ổn định, ví dụ RIDE_NOT_FOUND")
    message_for_user: str = Field(
        description="Câu giải thích cho khách bằng tiếng Việt. KHÔNG chứa stacktrace, "
        "tên bảng, hay bất kỳ chi tiết kỹ thuật nào."
    )
    detail_for_log: str | None = Field(
        default=None, description="Chi tiết kỹ thuật — chỉ ghi vào tool_calls, không gửi cho LLM."
    )
    retry_after_seconds: float | None = None


class ToolResult(BaseModel, Generic[T]):
    """Bao ngoài mọi kết quả tool. Graph luôn kiểm tra `ok` trước khi đọc `data`."""

    ok: bool
    data: T | None = None
    error: ToolError | None = None
    replayed: bool = Field(
        default=False,
        description="True khi lần gọi này trùng idempotency_key và kết quả được lấy lại "
        "từ lần trước thay vì thực thi lại (ADR-005).",
    )
    latency_ms: int | None = None


# ===========================================================================
# Lớp nền
# ===========================================================================
class ToolInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    conversation_id: str = Field(description="Phiên hội thoại phát sinh lời gọi này")


class WriteToolInput(ToolInput):
    """Lớp nền cho mọi tool có ghi dữ liệu. Bắt buộc có idempotency_key (ADR-005)."""

    idempotency_key: str | None = Field(
        default=None,
        description="Bỏ trống thì tầng thực thi tự sinh bằng build_idempotency_key(). "
        "LLM không cần và không nên tự đặt giá trị này.",
    )

    def build_idempotency_key(self, tool_name: str) -> str:
        """Sinh key xác định từ nội dung yêu cầu.

        Cùng một yêu cầu trong cùng một hội thoại luôn ra cùng một key, nên lần
        gọi thứ hai sẽ va vào ràng buộc UNIQUE ở DB thay vì thực thi lại.
        `conversation_id` nằm trong key để hai khách khác nhau yêu cầu giống
        nhau không chặn nhầm lẫn nhau.
        """
        payload = self.model_dump(exclude={"idempotency_key"}, mode="json")
        canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False)
        digest = hashlib.sha256(f"{tool_name}|{canonical}".encode()).hexdigest()
        return f"{tool_name}:{digest[:32]}"


# ===========================================================================
# 1. get_ride_history — tra cứu lịch sử chuyến (chỉ đọc)
# ===========================================================================
class GetRideHistoryInput(ToolInput):
    customer_id: str
    limit: Annotated[int, Field(ge=1, le=20)] = 5
    since_days: Annotated[int, Field(ge=1, le=365)] = 30
    status_filter: (
        list[Literal["COMPLETED", "CANCELLED", "IN_PROGRESS", "ASSIGNED", "PENDING"]] | None
    ) = None


class RideSummary(BaseModel):
    ride_code: str = Field(pattern=RIDE_CODE_PATTERN)
    service_type: ServiceType
    status: str
    pickup_address: str = pii_field("Điểm đón — placeholder khi vào LLM")
    dropoff_address: str = pii_field("Điểm đến — placeholder khi vào LLM")
    final_fare: int | None = Field(default=None, description="Số tiền thực trừ, đơn vị VNĐ")
    requested_at: datetime


class GetRideHistoryOutput(BaseModel):
    rides: list[RideSummary]
    total_found: int


# ===========================================================================
# 2. get_ride_detail — chi tiết một chuyến, kèm dòng thời gian (chỉ đọc)
# ===========================================================================
class GetRideDetailInput(ToolInput):
    ride_code: str = Field(pattern=RIDE_CODE_PATTERN)


class RideEvent(BaseModel):
    event_type: str
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class PaymentRecord(BaseModel):
    amount: int
    method: str
    status: str
    transaction_ref: str
    charged_at: datetime


class GetRideDetailOutput(RideSummary):
    """Chi tiết đủ để agent **giải thích** một khoản phí, thay vì phán đoán."""

    driver_name: str | None = pii_field("Tên tài xế", default=None)
    planned_distance_km: float | None = None
    actual_distance_km: float | None = None
    quoted_fare: int | None = Field(default=None, description="Giá hiển thị lúc khách xác nhận")
    cancel_fee: int = 0
    cancelled_at: datetime | None = None
    completed_at: datetime | None = None
    events: list[RideEvent] = Field(default_factory=list)
    payments: list[PaymentRecord] = Field(default_factory=list)

    @property
    def deviation_pct(self) -> float | None:
        """Phần trăm vượt lộ trình — so với route.deviation_threshold_pct để xét hoàn tiền."""
        if not self.planned_distance_km or not self.actual_distance_km:
            return None
        return round((self.actual_distance_km / self.planned_distance_km - 1) * 100, 1)


# ===========================================================================
# 3. estimate_fare — ước tính cước cho chuyến CHƯA tồn tại (chỉ đọc)
# ===========================================================================
class EstimateFareInput(ToolInput):
    pickup_address: str = pii_field("Điểm đón")
    dropoff_address: str = pii_field("Điểm đến")
    service_type: ServiceType
    distance_km: Annotated[float, Field(gt=0, le=200)] | None = None
    pickup_time: datetime | None = Field(
        default=None, description="Bỏ trống nghĩa là ngay bây giờ. Dùng để xét phụ phí đêm 22h–6h."
    )
    extra_stops: Annotated[int, Field(ge=0, le=2)] = 0


class FareBreakdown(BaseModel):
    """Tách bạch từng khoản để agent trả lời được câu 'sao lại đắt thế'."""

    base_fare: int
    distance_fare: int
    night_surcharge: int = 0
    extra_stop_fee: int = 0
    total_fare: int
    currency: Literal["VND"] = "VND"
    policy_source: str = Field(description="File KB làm căn cứ, ví dụ 01_pricing_and_surcharges.md")


# ===========================================================================
# 4. book_ride — đặt chuyến mới (GHI)
# ===========================================================================
class BookRideInput(WriteToolInput):
    customer_id: str
    pickup_address: str = pii_field("Điểm đón", min_length=3)
    dropoff_address: str = pii_field("Điểm đến", min_length=3)
    service_type: ServiceType
    payment_method: Literal["CASH", "CARD", "WALLET"] = "CASH"
    note_for_driver: str | None = Field(default=None, max_length=200)


class BookRideOutput(BaseModel):
    ride_code: str = Field(pattern=RIDE_CODE_PATTERN)
    status: Literal["PENDING", "ASSIGNED"]
    estimated_fare: int
    driver_name: str | None = pii_field("Tên tài xế nếu đã điều phối được", default=None)
    eta_minutes: int | None = None


# ===========================================================================
# 5. cancel_ride — huỷ chuyến (GHI)
# ===========================================================================
class CancelRideInput(WriteToolInput):
    ride_code: str = Field(pattern=RIDE_CODE_PATTERN)
    reason: str = Field(min_length=1, max_length=300)


class CancelRideOutput(BaseModel):
    ride_code: str
    cancelled_at: datetime
    cancel_fee: int = Field(description="0 nếu huỷ trong cửa sổ miễn phí")
    fee_waived: bool
    fee_explanation: str = Field(
        description="Vì sao có hoặc không có phí, dẫn chiếu chính sách. Đây là phần khách "
        "hay khiếu nại nhất nên bắt buộc phải có."
    )


# ===========================================================================
# 6. modify_ride — đổi điểm đến / thêm điểm dừng (GHI)
# ===========================================================================
class ModifyRideInput(WriteToolInput):
    ride_code: str = Field(pattern=RIDE_CODE_PATTERN)
    new_dropoff_address: str | None = pii_field("Điểm đến mới", default=None)
    add_stop_address: str | None = pii_field("Điểm dừng thêm", default=None)

    @model_validator(mode="after")
    def at_least_one_change(self) -> ModifyRideInput:
        # Phải là model_validator, không phải field_validator: field_validator KHÔNG chạy
        # khi trường vắng mặt và có default, nên LLM gọi tool rỗng sẽ lọt qua.
        if self.new_dropoff_address is None and self.add_stop_address is None:
            raise ValueError("Phải có ít nhất một thay đổi: đổi điểm đến hoặc thêm điểm dừng")
        return self


class ModifyRideOutput(BaseModel):
    ride_code: str
    new_dropoff_address: str | None = pii_field("Điểm đến sau khi đổi", default=None)
    fare_delta: int = Field(description="Chênh lệch cước, có thể âm")
    new_estimated_fare: int
    extra_stop_fee: int = 0


# ===========================================================================
# 7. request_refund — yêu cầu hoàn tiền (GHI, có thể chạm HITL)
# ===========================================================================
class RefundReasonCode(StrEnum):
    DOUBLE_CHARGE = "DOUBLE_CHARGE"
    ROUTE_INEFFICIENCY = "ROUTE_INEFFICIENCY"
    FARE_DISCREPANCY = "FARE_DISCREPANCY"
    WRONG_CANCEL_FEE = "WRONG_CANCEL_FEE"
    SERVICE_INTERRUPTION = "SERVICE_INTERRUPTION"
    OTHER = "OTHER"


class RequestRefundInput(WriteToolInput):
    customer_id: str
    ride_code: str = Field(pattern=RIDE_CODE_PATTERN)
    amount: Annotated[int, Field(gt=0, le=10_000_000)] = Field(
        description="Số tiền đề nghị hoàn, VNĐ"
    )
    reason_code: RefundReasonCode
    reason_detail: str = Field(min_length=5, max_length=1000)


class RequestRefundOutput(BaseModel):
    """LLM **không** được tự quyết duyệt hay không.

    Trường `status` do tầng thực thi tính ra sau khi đối chiếu
    `business_config` (ADR-006), rồi mới trả về cho graph.
    """

    refund_code: str
    amount: int
    status: Literal["AUTO_APPROVED", "PENDING_HITL"]
    threshold_applied: int = Field(description="Ngưỡng lấy từ refund.auto_approve_max_vnd lúc chạy")
    escalation_reason: str | None = Field(
        default=None, description="Vì sao phải chuyển người duyệt — hiện cho CSKH xem trên dashboard"
    )
    estimated_completion: str | None = Field(
        default=None, description="Thời gian hoàn tiền dự kiến theo phương thức thanh toán gốc"
    )
    ticket_code: str | None = None


# ===========================================================================
# 8. create_ticket — tạo phiếu khiếu nại (GHI)
# ===========================================================================
class TicketCategory(StrEnum):
    DRIVER_CONDUCT = "DRIVER_CONDUCT"
    LOST_ITEM = "LOST_ITEM"
    FARE_DISPUTE = "FARE_DISPUTE"
    SAFETY = "SAFETY"
    OTHER = "OTHER"


class CreateTicketInput(WriteToolInput):
    customer_id: str
    category: TicketCategory
    description: str = Field(min_length=5, max_length=2000)
    ride_code: str | None = Field(default=None, pattern=RIDE_CODE_PATTERN)
    severity: Literal["LOW", "NORMAL", "HIGH", "CRITICAL"] = "NORMAL"

    @model_validator(mode="after")
    def ride_required_for_some_categories(self) -> CreateTicketInput:
        needs_ride = {TicketCategory.DRIVER_CONDUCT, TicketCategory.LOST_ITEM,
                      TicketCategory.FARE_DISPUTE}
        if self.ride_code is None and self.category in needs_ride:
            raise ValueError(
                "Khiếu nại tài xế / thất lạc đồ / tranh chấp cước bắt buộc phải có mã chuyến. "
                "Agent phải hỏi khách hoặc tra từ lịch sử trước khi gọi tool."
            )
        return self


class CreateTicketOutput(BaseModel):
    ticket_code: str
    category: TicketCategory
    severity: str
    status: Literal["OPEN", "IN_PROGRESS"]
    sla_hours: int = Field(description="Cam kết thời gian phản hồi, theo severity")


# ===========================================================================
# Sổ đăng ký tool
# ===========================================================================
class ToolSpec(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str
    writes_data: bool
    input_model: type[BaseModel]
    output_model: type[BaseModel]
    intents: list[str] = Field(description="Intent nào được phép gọi tool này")
    description: str


TOOL_REGISTRY: dict[str, ToolSpec] = {
    spec.name: spec
    for spec in [
        ToolSpec(name="get_ride_history", writes_data=False,
                 input_model=GetRideHistoryInput, output_model=GetRideHistoryOutput,
                 intents=["trip.lookup", "refund.request", "complaint.driver", "complaint.lost_item"],
                 description="Lấy danh sách chuyến gần đây của khách"),
        ToolSpec(name="get_ride_detail", writes_data=False,
                 input_model=GetRideDetailInput, output_model=GetRideDetailOutput,
                 intents=["trip.lookup", "refund.request", "booking.cancel", "booking.modify",
                          "complaint.driver", "complaint.lost_item"],
                 description="Chi tiết một chuyến kèm dòng thời gian và lịch sử thanh toán"),
        ToolSpec(name="estimate_fare", writes_data=False,
                 input_model=EstimateFareInput, output_model=FareBreakdown,
                 intents=["fare.inquiry", "booking.create"],
                 description="Ước tính cước cho chuyến chưa tồn tại, tách rõ từng khoản"),
        ToolSpec(name="book_ride", writes_data=True,
                 input_model=BookRideInput, output_model=BookRideOutput,
                 intents=["booking.create"], description="Đặt chuyến mới"),
        ToolSpec(name="cancel_ride", writes_data=True,
                 input_model=CancelRideInput, output_model=CancelRideOutput,
                 intents=["booking.cancel"], description="Huỷ chuyến và tính phí huỷ theo chính sách"),
        ToolSpec(name="modify_ride", writes_data=True,
                 input_model=ModifyRideInput, output_model=ModifyRideOutput,
                 intents=["booking.modify"], description="Đổi điểm đến hoặc thêm điểm dừng"),
        ToolSpec(name="request_refund", writes_data=True,
                 input_model=RequestRefundInput, output_model=RequestRefundOutput,
                 intents=["refund.request"],
                 description="Tạo yêu cầu hoàn tiền. Tầng thực thi tự quyết auto-duyệt hay chuyển HITL"),
        ToolSpec(name="create_ticket", writes_data=True,
                 input_model=CreateTicketInput, output_model=CreateTicketOutput,
                 intents=["complaint.driver", "complaint.lost_item", "refund.request"],
                 description="Tạo phiếu khiếu nại"),
    ]
}

WRITE_TOOLS = [name for name, spec in TOOL_REGISTRY.items() if spec.writes_data]
READ_TOOLS = [name for name, spec in TOOL_REGISTRY.items() if not spec.writes_data]


def pii_fields_of(model: type[BaseModel]) -> list[str]:
    """Liệt kê tên các trường đã đánh dấu PII — tokenizer dùng ở T-010."""
    out = []
    for name, field in model.model_fields.items():
        extra = field.json_schema_extra or {}
        if isinstance(extra, dict) and extra.get("pii"):
            out.append(name)
    return out
