"""Chặn các thao tác dữ liệu demo nguy hiểm trên production."""
from __future__ import annotations

from src.backend.config.env import env_str


def _enabled(name: str) -> bool:
    return (env_str(name, "false") or "").lower() in {"1", "true", "yes", "on"}


def ensure_demo_operation_allowed(flag_name: str, operation: str) -> None:
    environment = (env_str("ENVIRONMENT", "development") or "development").lower()
    if environment == "production":
        raise RuntimeError(
            f"Không được {operation} trên ENVIRONMENT=production. "
            "Hãy dùng database staging riêng."
        )
    if not _enabled(flag_name):
        raise RuntimeError(
            f"Muốn {operation}, phải đặt {flag_name}=true trong môi trường không phải production."
        )
