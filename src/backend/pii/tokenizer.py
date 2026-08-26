"""Token hoá PII trước khi dữ liệu vào context của LLM (ADR-004).

Nguyên tắc: **LLM không thể làm lộ thứ nó chưa từng nhìn thấy.**

Khác biệt cốt lõi so với lọc regex ở đầu ra: ở đây ta không *đoán* xem chuỗi nào
là PII, mà *biết chắc* — vì dữ liệu đi ra từ DB theo đúng các trường đã được đánh
dấu `pii_field()` trong `tools/contracts.py`. Regex chỉ bắt được thứ nó lường
trước; token hoá theo trường thì không bỏ sót, và cũng không phân biệt được
tên tài xế với chữ thường như regex.

Đo ở D3 trước khi có tầng này:
- chỉ dặn trong system prompt: **5/20 ca lộ**
- thêm lưới regex ở đầu ra: **2/20** — và regex không thể về 0

Vòng đời một giá trị:

    DB  --tokenize-->  <PHONE_C7>  --LLM-->  <PHONE_C7>  --mask-->  0912****78
                                                          \\
                                                           --detokenize--> giá trị thật
                                                              (chỉ cho CSKH có quyền)
"""
from __future__ import annotations

import hashlib
import re
import threading
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel

from src.backend.tools.contracts import pii_fields_of

# Trường nào thuộc loại PII nào. Quyết định cách hiển thị khi che.
FIELD_KIND = {
    "phone": "PHONE",
    "driver_phone": "PHONE",
    "pickup_address": "ADDR",
    "dropoff_address": "ADDR",
    "new_dropoff_address": "ADDR",
    "add_stop_address": "ADDR",
    "driver_name": "NAME",
    "full_name": "NAME",
    "plate_number": "PLATE",
}

PLACEHOLDER_RE = re.compile(r"<(PHONE|ADDR|NAME|PLATE)_([0-9A-F]{2,4})>")

# Giá trị ngắn hơn mức này không đáng token hoá và dễ gây thay nhầm
_MIN_LEN = 4


def _kind_for(field_name: str) -> str:
    return FIELD_KIND.get(field_name, "ADDR")


@dataclass
class PiiVault:
    """Kho ánh xạ placeholder ↔ giá trị thật, phạm vi một hội thoại.

    Cùng một số điện thoại trong cùng hội thoại luôn nhận cùng một placeholder,
    nhờ vậy LLM vẫn suy luận được là "tài xế chuyến A và chuyến B là một người"
    mà không hề biết người đó là ai.
    """

    conversation_id: str
    _to_placeholder: dict[str, str] = field(default_factory=dict)
    _to_value: dict[str, str] = field(default_factory=dict)

    def placeholder_for(self, value: str, kind: str) -> str:
        existing = self._to_placeholder.get(value)
        if existing:
            return existing
        digest = hashlib.sha256(f"{self.conversation_id}|{value}".encode()).hexdigest()
        token = f"<{kind}_{digest[:2].upper()}>"
        # Tránh đụng độ hiếm gặp giữa hai giá trị khác nhau
        suffix = 2
        while token in self._to_value and self._to_value[token] != value:
            token = f"<{kind}_{digest[:suffix + 2].upper()}>"
            suffix += 2
        self._to_placeholder[value] = token
        self._to_value[token] = value
        return token

    def tokenize_field(self, field_name: str, value: Any) -> Any:
        if not isinstance(value, str) or len(value.strip()) < _MIN_LEN:
            return value
        return self.placeholder_for(value.strip(), _kind_for(field_name))

    def tokenize_text(self, text: str) -> str:
        """Quét văn bản tự do và thay mọi giá trị đã biết trong kho.

        Cần thiết vì PII còn lẫn trong các trường không được đánh dấu — ví dụ mô
        tả khiếu nại do chính khách nhập, hay `reason_detail` của yêu cầu hoàn tiền.
        Thay giá trị dài trước để không cắt vụn giá trị dài bằng giá trị ngắn.
        """
        if not text:
            return text
        for value in sorted(self._to_placeholder, key=len, reverse=True):
            if value in text:
                text = text.replace(value, self._to_placeholder[value])
        return text

    def detokenize(self, text: str) -> str:
        """Khôi phục giá trị thật. CHỈ dùng khi hiển thị cho vai trò có quyền."""
        def restore(match: re.Match[str]) -> str:
            return self._to_value.get(match.group(0), match.group(0))
        return PLACEHOLDER_RE.sub(restore, text)

    def mask_for_display(self, text: str) -> str:
        """Đổi placeholder còn sót thành dạng che được, thân thiện với khách.

        Nếu LLM cố đọc placeholder ra ngoài, khách sẽ thấy `0912****78` thay vì
        `<PHONE_C7>` — vẫn không lộ, mà cũng không lộ luôn cả cơ chế bên trong.
        """
        def mask(match: re.Match[str]) -> str:
            value = self._to_value.get(match.group(0))
            kind = match.group(1)
            if not value:
                return "(đã ẩn)"
            if kind == "PHONE":
                digits = re.sub(r"\D", "", value)
                return f"{digits[:4]}****{digits[-2:]}" if len(digits) >= 6 else "(đã ẩn)"
            if kind == "NAME":
                parts = value.split()
                return f"{parts[0]} ***" if parts else "(đã ẩn)"
            if kind == "PLATE":
                return f"{value[:3]}***"
            head = value.split(",")[0].split()[0] if value.split() else ""
            return f"{head} ***" if head else "(đã ẩn)"
        return PLACEHOLDER_RE.sub(mask, text)

    @property
    def size(self) -> int:
        return len(self._to_placeholder)


_VAULTS: dict[str, PiiVault] = {}
_LOCK = threading.Lock()


def get_vault(conversation_id: str | None) -> PiiVault:
    """Một kho cho mỗi hội thoại, dùng chung trong tiến trình."""
    key = conversation_id or "khong-co-hoi-thoai"
    with _LOCK:
        vault = _VAULTS.get(key)
        if vault is None:
            vault = PiiVault(conversation_id=key)
            _VAULTS[key] = vault
        return vault


def forget_vault(conversation_id: str) -> None:
    with _LOCK:
        _VAULTS.pop(conversation_id, None)


def tokenize_model(model: BaseModel, vault: PiiVault) -> BaseModel:
    """Trả về bản sao của model với mọi trường PII đã được thay bằng placeholder.

    Đệ quy xuống model con và danh sách model con, vì `GetRideHistoryOutput` chứa
    một danh sách `RideSummary` mà mỗi phần tử đều mang địa chỉ đón/trả.
    """
    updates: dict[str, Any] = {}
    pii_names = set(pii_fields_of(type(model)))

    for name in type(model).model_fields:
        value = getattr(model, name, None)
        if value is None:
            continue
        if name in pii_names:
            updates[name] = vault.tokenize_field(name, value)
        elif isinstance(value, BaseModel):
            updates[name] = tokenize_model(value, vault)
        elif isinstance(value, list) and value and isinstance(value[0], BaseModel):
            updates[name] = [tokenize_model(item, vault) for item in value]
        elif isinstance(value, str) and vault.size:
            # Trường văn bản tự do có thể lẫn PII đã biết
            cleaned = vault.tokenize_text(value)
            if cleaned != value:
                updates[name] = cleaned

    return model.model_copy(update=updates) if updates else model


class StreamMasker:
    """Che placeholder trên luồng stream, chịu được việc bị cắt giữa chừng.

    Không thể che từng mảnh một cách ngây thơ: model có thể phát ra `<ADDR` ở
    mảnh này và `_48>` ở mảnh sau. Ghép nhầm là khách nhìn thấy nguyên placeholder.

    Cách làm: giữ lại phần đuôi *có thể* đang là một placeholder dở dang, chỉ đẩy
    ra phần chắc chắn an toàn. `flush()` xả nốt phần còn treo khi luồng kết thúc.

    Cái giá là token đầu tiên có thể bị giữ lại một nhịp nếu nó bắt đầu bằng `<` —
    hiếm gặp, và đổi lấy việc không bao giờ lộ placeholder ra giao diện.
    """

    # Dài nhất một placeholder có thể có: "<PLATE_ABCD>" = 12 ký tự
    _MAX_PLACEHOLDER = 12

    def __init__(self, vault: PiiVault) -> None:
        self._vault = vault
        self._buffer = ""

    def feed(self, delta: str) -> str:
        self._buffer += delta
        safe = self._vault.mask_for_display(self._buffer)

        # Tìm dấu '<' cuối cùng còn chưa được đóng — đó là ranh giới an toàn
        cut = safe.rfind("<")
        if cut == -1 or ">" in safe[cut:]:
            self._buffer = ""
            return safe
        # Đuôi quá dài để còn là placeholder hợp lệ thì không phải placeholder
        if len(safe) - cut > self._MAX_PLACEHOLDER:
            self._buffer = ""
            return safe
        self._buffer = safe[cut:]
        return safe[:cut]

    def flush(self) -> str:
        remaining = self._vault.mask_for_display(self._buffer)
        self._buffer = ""
        return remaining
