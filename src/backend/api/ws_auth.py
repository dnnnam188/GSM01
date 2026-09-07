"""One-time WebSocket tickets cho trình duyệt.

Browser WebSocket API không cho đặt ``Authorization`` header tuỳ ý. Access
token dài hạn vì thế không được đưa thẳng vào URL; API HTTP cấp một ticket
ngắn hạn, dùng một lần. Ticket nằm trong memory vì free-tier chỉ chạy một
worker. Khi scale nhiều worker, thay store này bằng PostgreSQL hoặc Redis.
"""
from __future__ import annotations

import secrets
from collections.abc import Callable
from dataclasses import dataclass
from time import monotonic
from typing import Any


@dataclass(frozen=True)
class _Ticket:
    payload: dict[str, Any]
    expires_at: float


class WebSocketTicketStore:
    def __init__(
        self,
        ttl_seconds: int = 30,
        *,
        clock: Callable[[], float] = monotonic,
    ) -> None:
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds phải lớn hơn 0")
        self.ttl_seconds = ttl_seconds
        self._clock = clock
        self._tickets: dict[str, _Ticket] = {}

    def _cleanup(self, now: float) -> None:
        expired = [key for key, ticket in self._tickets.items() if ticket.expires_at <= now]
        for key in expired:
            self._tickets.pop(key, None)

    def issue(self, payload: dict[str, Any]) -> tuple[str, int]:
        now = self._clock()
        self._cleanup(now)
        token = secrets.token_urlsafe(32)
        self._tickets[token] = _Ticket(dict(payload), now + self.ttl_seconds)
        return token, self.ttl_seconds

    def consume(self, token: str) -> dict[str, Any] | None:
        if not token:
            return None
        now = self._clock()
        ticket = self._tickets.pop(token, None)
        if ticket is None or ticket.expires_at <= now:
            return None
        return dict(ticket.payload)

    def clear(self) -> None:
        self._tickets.clear()
