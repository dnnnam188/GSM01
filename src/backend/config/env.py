"""Đọc biến môi trường một cách chịu lỗi và báo lỗi rõ ràng.

Vì sao cần cả một module cho việc này: bản deploy trên Render từng chết ngay lúc
khởi động vì `JWT_EXPIRE_MINUTES` bị dính một dấu backtick ở cuối (`720\u0060`) —
dấu vết của việc sao chép từ một đoạn văn bản có định dạng mã. Thông báo lỗi khi
đó là `ValueError: invalid literal for int() with base 10` kèm nguyên vẹn
traceback của uvicorn, **không hề nói biến nào sai**.

Hai việc module này làm:
1. **Gột sạch** ký tự trang trí hay dính vào lúc sao chép: khoảng trắng, nháy đơn,
   nháy kép, backtick. Không giá trị cấu hình hợp lệ nào chứa chúng.
2. **Báo lỗi nêu đích danh** tên biến và giá trị đang sai, để người deploy sửa
   được ngay mà không phải đọc traceback.
"""
from __future__ import annotations

import os

_RAC = " \t\r\n'\"`"


def env_str(name: str, default: str | None = None) -> str | None:
    raw = os.getenv(name)
    if raw is None:
        return default
    cleaned = raw.strip(_RAC)
    return cleaned if cleaned else default


def env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    cleaned = raw.strip(_RAC)
    if not cleaned:
        return default
    try:
        return int(cleaned)
    except ValueError:
        raise RuntimeError(
            f"Biến môi trường {name} phải là một số nguyên, nhưng đang là {raw!r}. "
            f"Kiểm tra xem có lẫn dấu nháy, backtick hay khoảng trắng khi dán giá trị không."
        ) from None


def env_list(name: str, default: str = "") -> list[str]:
    raw = env_str(name, default) or ""
    return [item.strip(_RAC) for item in raw.split(",") if item.strip(_RAC)]
