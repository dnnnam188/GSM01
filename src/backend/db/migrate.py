"""Áp dụng migration database theo thứ tự, có ghi nhận phiên bản.

``schema.sql`` là migration khởi đầu của dự án. Từ sau mốc này, thay đổi
production phải thêm migration mới và không được sửa ngược migration đã chạy.
Runner vẫn giữ lệnh ``apply_schema`` cũ để không phá quy trình deploy hiện tại.
"""
from __future__ import annotations

from pathlib import Path

from src.backend.db.connection import get_connection

SCHEMA_PATH = Path(__file__).with_name("schema.sql")
MIGRATIONS_DIR = Path(__file__).with_name("migrations")
INITIAL_VERSION = "001_initial_schema"


def migration_files() -> list[tuple[str, Path]]:
    files = [(INITIAL_VERSION, SCHEMA_PATH)]
    files.extend(
        (path.stem, path)
        for path in sorted(MIGRATIONS_DIR.glob("*.sql"))
        if path.stem != INITIAL_VERSION
    )
    return files


def apply_migrations() -> list[str]:
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations ("
            "version TEXT PRIMARY KEY, applied_at TIMESTAMPTZ NOT NULL DEFAULT now()"
            ")"
        )
        cur.execute("SELECT version FROM schema_migrations ORDER BY version")
        applied = {row[0] for row in cur.fetchall()}
        for version, path in migration_files():
            if version in applied:
                continue
            cur.execute(path.read_text(encoding="utf-8"))
            cur.execute("INSERT INTO schema_migrations (version) VALUES (%s)", (version,))
            applied.add(version)
    return sorted(applied)


def main() -> None:
    versions = apply_migrations()
    print("Migration database đã áp dụng:")
    for version in versions:
        print(f"  - {version}")


if __name__ == "__main__":
    main()
