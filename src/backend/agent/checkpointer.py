"""Checkpointer Postgres cho LangGraph (ADR-003).

Vì sao phải lưu xuống Postgres chứ không giữ trong bộ nhớ: gói free của Render
ngủ sau ~15 phút không có request rồi khởi động lại tiến trình. Một yêu cầu hoàn
tiền đang chờ CSKH duyệt có thể nằm đó hàng giờ. Checkpointer trong bộ nhớ nghĩa
là mọi ca chờ duyệt bốc hơi sau mỗi lần server ngủ dậy — đúng thứ không được phép
xảy ra với tiền của khách.

Dùng `AsyncConnectionPool` thay vì `from_conn_string`: `from_conn_string` là một
context manager, đóng kết nối khi thoát khối lệnh, nên không dùng được cho tiến
trình sống lâu.
"""
from __future__ import annotations

import asyncio
import sys

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg_pool import AsyncConnectionPool

from src.backend.db.connection import get_database_url

# Đặt ngay tại module này thay vì ở từng điểm vào: BẤT KỲ ai dùng checkpointer đều
# cần Selector loop trên Windows — `run_dev.py`, `pytest`, script rời, bộ eval.
# Lặp lại ở mỗi entrypoint là chắc chắn sẽ quên một chỗ, và triệu chứng khi quên là
# treo 30 giây rồi `PoolTimeout`, không hề nhắc gì tới event loop.
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

_pool: AsyncConnectionPool | None = None
_saver: AsyncPostgresSaver | None = None
_lock = asyncio.Lock()


async def get_checkpointer() -> AsyncPostgresSaver:
    """Khởi tạo một lần, dùng chung cho cả tiến trình."""
    global _pool, _saver
    async with _lock:
        if _saver is not None:
            return _saver
        _pool = AsyncConnectionPool(
            conninfo=get_database_url(),
            min_size=1,
            max_size=4,
            # LangGraph yêu cầu autocommit; thiếu dòng này sẽ lỗi khi ghi checkpoint
            kwargs={"autocommit": True, "prepare_threshold": 0},
            open=False,
        )
        await _pool.open()
        _saver = AsyncPostgresSaver(_pool)
        # Tạo bảng checkpoint nếu chưa có. Chạy lại được nhiều lần.
        await _saver.setup()
        return _saver


async def close_checkpointer() -> None:
    global _pool, _saver
    async with _lock:
        if _pool is not None:
            await _pool.close()
        _pool, _saver = None, None
