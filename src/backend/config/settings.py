"""Cấu hình đọc từ biến môi trường. Không hardcode secret (xem .ai/rules/security.md)."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

from src.backend.config.env import env_int, env_list, env_str

PROJECT_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(dotenv_path=PROJECT_ROOT / ".env")


class Settings:
    def __init__(self) -> None:
        self.database_url = env_str("DATABASE_URL") or ""
        self.jwt_secret = env_str("JWT_SECRET", "") or ""
        self.jwt_algorithm = "HS256"
        self.jwt_expire_minutes = env_int("JWT_EXPIRE_MINUTES", 720)
        # Danh sách origin cho CORS. Trên Render đặt CORS_ORIGINS=https://<app>.vercel.app
        self.cors_origins = env_list("CORS_ORIGINS", "http://localhost:3000")
        self.environment = env_str("ENVIRONMENT", "development") or "development"

        if not self.database_url:
            raise RuntimeError("Thiếu DATABASE_URL trong biến môi trường — xem .env.example")
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
