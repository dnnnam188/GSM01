"""Sổ đăng ký kết nối WebSocket đang mở, để đẩy tin ngược về đúng phiên của khách.

Cần thiết cho luồng HITL (ADR-003): CSKH bấm Duyệt trên dashboard, và kết quả
phải hiện lên **chính khung chat mà khách đang mở**, chứ không bắt khách hỏi lại.

Sổ này nằm trong bộ nhớ tiến trình, nên chỉ đúng khi chạy một tiến trình — đúng
với gói free của Render. Nếu về sau chạy nhiều worker thì phải thay bằng
pub/sub (Redis hoặc `LISTEN/NOTIFY` của Postgres); chỗ cần đổi gói gọn trong file này.
Khách không online lúc đó cũng không mất tin: câu trả lời đã được ghi vào bảng
`messages`, nên lần sau mở lại vẫn thấy.
"""
from __future__ import annotations

import asyncio
from typing import Any

from fastapi import WebSocket


class ConnectionHub:
    def __init__(self) -> None:
        self._by_conversation: dict[str, set[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def register(self, conversation_id: str, websocket: WebSocket) -> None:
        async with self._lock:
            self._by_conversation.setdefault(conversation_id, set()).add(websocket)

    async def unregister(self, conversation_id: str, websocket: WebSocket) -> None:
        async with self._lock:
            sockets = self._by_conversation.get(conversation_id)
            if not sockets:
                return
            sockets.discard(websocket)
            if not sockets:
                self._by_conversation.pop(conversation_id, None)

    async def push(self, conversation_id: str, payload: dict[str, Any]) -> int:
        """Đẩy tới mọi kết nối của hội thoại. Trả về số kết nối đã nhận được."""
        async with self._lock:
            sockets = list(self._by_conversation.get(conversation_id, ()))
        delivered = 0
        for socket in sockets:
            try:
                await socket.send_json(payload)
                delivered += 1
            except Exception:  # noqa: BLE001 — kết nối chết không được làm hỏng luồng duyệt
                await self.unregister(conversation_id, socket)
        return delivered


hub = ConnectionHub()
