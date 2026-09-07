"""Các bộ giới hạn nhẹ, không cần thêm dịch vụ cho Render free.

Free-tier GSM-01 hiện chỉ chạy một worker, vì vậy một sliding window trong
process đủ để chặn burst đăng nhập và giữ quota Gemini không bị một user dùng
hết. Khi chạy nhiều worker, module này phải được thay bằng backend dùng chung
(PostgreSQL/Redis); không nên giả vờ rằng bộ đếm trong memory là global.
"""
from __future__ import annotations

from collections import defaultdict, deque
from collections.abc import Callable
from math import ceil
from threading import Lock
from time import monotonic


class SlidingWindowLimiter:
    """Giới hạn số lần gọi trong một cửa sổ thời gian trượt.

    ``allow`` không ngủ và không chặn event loop. Khi bị từ chối, caller có thể
    dùng ``retry_after`` để trả thông tin đủ dùng cho client mà không lộ state.
    """

    def __init__(
        self,
        limit: int,
        window_seconds: int,
        *,
        clock: Callable[[], float] = monotonic,
    ) -> None:
        if limit <= 0:
            raise ValueError("limit phải lớn hơn 0")
        if window_seconds <= 0:
            raise ValueError("window_seconds phải lớn hơn 0")
        self.limit = limit
        self.window_seconds = window_seconds
        self._clock = clock
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def _prune(self, key: str, now: float) -> deque[float]:
        events = self._events[key]
        cutoff = now - self.window_seconds
        while events and events[0] <= cutoff:
            events.popleft()
        if not events:
            self._events.pop(key, None)
            return deque()
        return events

    def allow(self, key: str) -> bool:
        now = self._clock()
        with self._lock:
            events = self._prune(key, now)
            if len(events) >= self.limit:
                return False
            if key not in self._events:
                self._events[key] = events
            events.append(now)
            return True

    def retry_after(self, key: str) -> int:
        """Số giây tối thiểu nên chờ trước khi thử lại (luôn >= 1 khi bị đầy)."""
        now = self._clock()
        with self._lock:
            events = self._prune(key, now)
            if not events:
                return 0
            return max(1, ceil(events[0] + self.window_seconds - now))

    def clear(self) -> None:
        with self._lock:
            self._events.clear()
