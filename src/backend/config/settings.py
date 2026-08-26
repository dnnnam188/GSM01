"""Cấu hình đọc từ biến môi trường. Không hardcode secret (xem .ai/rules/security.md)."""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(dotenv_path=PROJECT_ROOT / ".env")


class Settings:
    def __init__(self) -> None:
        self.database_url = os.environ["DATABASE_URL"]
        self.jwt_secret = os.getenv("JWT_SECRET", "")
        self.jwt_algorithm = "HS256"
        self.jwt_expire_minutes = int(os.getenv("JWT_EXPIRE_MINUTES", "720"))
        # Danh sách origin cho CORS. Trên Render đặt CORS_ORIGINS=https://<app>.vercel.app
        self.cors_origins = [
            o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",") if o.strip()
        ]
        self.environment = os.getenv("ENVIRONMENT", "development")

        if not self.jwt_secret:
            raise RuntimeError("Thiếu JWT_SECRET trong .env — xem .env.example")
        if self.environment == "production" and "doi-thanh-chuoi" in self.jwt_secret:
            raise RuntimeError(
                "JWT_SECRET vẫn là giá trị mẫu trong .env.example. "
                "Đổi thành chuỗi ngẫu nhiên thật trước khi deploy."
            )


@lru_cache
def get_settings() -> Settings:
    return Settings()
