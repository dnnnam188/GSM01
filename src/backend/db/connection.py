"""Kết nối PostgreSQL (Neon). Đọc DATABASE_URL từ .env — không hardcode."""
from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path

import psycopg
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(dotenv_path=PROJECT_ROOT / ".env")


def get_database_url() -> str:
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("Thiếu DATABASE_URL trong .env — xem .env.example")
    return url


@contextmanager
def get_connection():
    """Mở kết nối, tự commit khi thoát khối lệnh mà không có lỗi."""
    conn = psycopg.connect(get_database_url())
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
