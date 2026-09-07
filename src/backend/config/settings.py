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
        self.jwt_expire_minutes = env_int("JWT_EXPIRE_MINUTES", 120)
        # Danh sách origin cho CORS. Trên Render đặt CORS_ORIGINS=https://<app>.vercel.app
        self.cors_origins = env_list("CORS_ORIGINS", "http://localhost:3000")
        self.environment = env_str("ENVIRONMENT", "development") or "development"

        # Free-tier chỉ chạy một worker. Khi scale nhiều worker, thay backend
        # của limiter/ticket bằng store dùng chung như PostgreSQL hoặc Redis.
        self.login_rate_limit = env_int("LOGIN_RATE_LIMIT", 10)
        self.login_rate_window_seconds = env_int("LOGIN_RATE_WINDOW_SECONDS", 60)
        self.chat_rate_limit = env_int("CHAT_RATE_LIMIT", 5)
        self.chat_rate_window_seconds = env_int("CHAT_RATE_WINDOW_SECONDS", 60)
        self.ws_ticket_ttl_seconds = env_int("WS_TICKET_TTL_SECONDS", 30)
        self.ws_idle_timeout_seconds = env_int("WS_IDLE_TIMEOUT_SECONDS", 1800)
        self.max_ws_frame_bytes = env_int("MAX_WS_FRAME_BYTES", 16_384)
        self.max_message_chars = env_int("MAX_MESSAGE_CHARS", 4_000)

        positive = {
            "JWT_EXPIRE_MINUTES": self.jwt_expire_minutes,
            "LOGIN_RATE_LIMIT": self.login_rate_limit,
            "LOGIN_RATE_WINDOW_SECONDS": self.login_rate_window_seconds,
            "CHAT_RATE_LIMIT": self.chat_rate_limit,
            "CHAT_RATE_WINDOW_SECONDS": self.chat_rate_window_seconds,
            "WS_TICKET_TTL_SECONDS": self.ws_ticket_ttl_seconds,
            "WS_IDLE_TIMEOUT_SECONDS": self.ws_idle_timeout_seconds,
            "MAX_WS_FRAME_BYTES": self.max_ws_frame_bytes,
            "MAX_MESSAGE_CHARS": self.max_message_chars,
        }
        invalid = [name for name, value in positive.items() if value <= 0]
        if invalid:
            raise RuntimeError("Các biến cấu hình phải lớn hơn 0: " + ", ".join(invalid))

        if not self.database_url:
            raise RuntimeError("Thiếu DATABASE_URL trong biến môi trường — xem .env.example")
        if not self.jwt_secret:
            raise RuntimeError("Thiếu JWT_SECRET trong .env — xem .env.example")
        if self.environment == "production" and "doi-thanh-chuoi" in self.jwt_secret:
            raise RuntimeError(
                "JWT_SECRET vẫn là giá trị mẫu trong .env.example. "
                "Đổi thành chuỗi ngẫu nhiên thật trước khi deploy."
            )
        if self.environment == "production" and len(self.jwt_secret) < 32:
            raise RuntimeError("JWT_SECRET production phải có ít nhất 32 ký tự.")
        if self.environment == "production" and (
            not self.cors_origins
            or self.cors_origins == ["*"]
            or any(not origin.startswith("https://") for origin in self.cors_origins)
        ):
            raise RuntimeError(
                "CORS_ORIGINS production phải chứa domain HTTPS của frontend, không dùng localhost/* của mẫu."
            )


@lru_cache
def get_settings() -> Settings:
    return Settings()
