from __future__ import annotations

import pytest

from src.backend.config.settings import Settings
from src.backend.db.demo_guard import ensure_demo_operation_allowed


def test_demo_operation_is_always_blocked_in_production(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("ALLOW_DEMO_SEED", "true")

    with pytest.raises(RuntimeError, match="production"):
        ensure_demo_operation_allowed("ALLOW_DEMO_SEED", "nạp dữ liệu demo")


def test_demo_operation_requires_explicit_staging_flag(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "staging")
    monkeypatch.delenv("ALLOW_DEMO_SEED", raising=False)

    with pytest.raises(RuntimeError, match="ALLOW_DEMO_SEED"):
        ensure_demo_operation_allowed("ALLOW_DEMO_SEED", "nạp dữ liệu demo")


def test_demo_operation_can_run_when_explicitly_enabled(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "staging")
    monkeypatch.setenv("ALLOW_DEMO_SEED", "true")
    ensure_demo_operation_allowed("ALLOW_DEMO_SEED", "nạp dữ liệu demo")


def _production_env(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@db.example/app")
    monkeypatch.setenv("JWT_SECRET", "x" * 48)


def test_production_rejects_localhost_cors(monkeypatch):
    _production_env(monkeypatch)
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:3000")
    with pytest.raises(RuntimeError, match="CORS_ORIGINS"):
        Settings()


def test_production_rejects_short_jwt_secret(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@db.example/app")
    monkeypatch.setenv("JWT_SECRET", "short")
    monkeypatch.setenv("CORS_ORIGINS", "https://staging.example.com")
    with pytest.raises(RuntimeError, match="JWT_SECRET"):
        Settings()
