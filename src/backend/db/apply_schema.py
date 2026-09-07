"""Tương thích ngược: chuyển sang migration runner có ghi nhận phiên bản."""
from __future__ import annotations

from src.backend.db.migrate import main

if __name__ == "__main__":
    main()
