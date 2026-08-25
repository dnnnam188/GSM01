"""Áp dụng schema.sql lên database. Chạy lại được nhiều lần (idempotent)."""
from __future__ import annotations

from pathlib import Path

from src.backend.db.connection import get_connection

SCHEMA_PATH = Path(__file__).with_name("schema.sql")


def main() -> None:
    sql = SCHEMA_PATH.read_text(encoding="utf-8")
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(sql)
        cur.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'public' ORDER BY table_name"
        )
        tables = [row[0] for row in cur.fetchall()]
    print(f"Đã áp dụng schema. {len(tables)} bảng trong public:")
    for name in tables:
        print(f"  - {name}")


if __name__ == "__main__":
    main()
