"""Cấu hình chung cho pytest.

Trên Windows, vòng lặp mặc định là `ProactorEventLoop`, mà `psycopg` bản async
KHÔNG chạy được trên đó — checkpointer Postgres của LangGraph sẽ treo 30 giây rồi
báo `PoolTimeout`. Cùng nguyên nhân với `run_dev.py`; xem ADR-003.

Đặt ở `conftest.py` để có hiệu lực trước khi bất kỳ test nào tạo event loop.
"""
from __future__ import annotations

import asyncio
import sys

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
