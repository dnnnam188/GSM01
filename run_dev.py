"""Khởi động server cho môi trường phát triển trên Windows.

    .venv/Scripts/python.exe run_dev.py

Vì sao cần file này thay vì gọi thẳng `uvicorn`: trên Windows, uvicorn chọn
`ProactorEventLoop`, mà `psycopg` bản async KHÔNG chạy được trên đó. Checkpointer
Postgres của LangGraph (ADR-003) dùng psycopg async, nên mọi kết nối sẽ hỏng với
thông báo "Psycopg cannot use the 'ProactorEventLoop' to run in async mode".

`loop="none"` bảo uvicorn đừng tự dựng vòng lặp, để ta tự dựng bằng Selector.

Trên Linux (môi trường Render) vòng lặp mặc định vốn đã là Selector, nên
production cứ chạy `uvicorn src.backend.main:app` như bình thường — xem render.yaml.
"""
from __future__ import annotations

import asyncio
import os
import sys

import uvicorn

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


def main() -> None:
    config = uvicorn.Config(
        "src.backend.main:app",
        host=os.getenv("HOST", "127.0.0.1"),
        port=int(os.getenv("PORT", "8000")),
        log_level=os.getenv("LOG_LEVEL", "warning"),
        loop="none",  # để đoạn set_event_loop_policy ở trên có hiệu lực
    )
    asyncio.run(uvicorn.Server(config).serve())


if __name__ == "__main__":
    main()
