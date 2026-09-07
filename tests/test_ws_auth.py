from __future__ import annotations

from src.backend.api.ws_auth import WebSocketTicketStore


def test_websocket_ticket_is_single_use():
    store = WebSocketTicketStore(30)
    ticket, ttl = store.issue({"id": "customer-1", "role": "customer"})

    assert ttl == 30
    assert store.consume(ticket) == {"id": "customer-1", "role": "customer"}
    assert store.consume(ticket) is None


def test_websocket_ticket_expires():
    now = [10.0]
    store = WebSocketTicketStore(5, clock=lambda: now[0])
    ticket, _ = store.issue({"id": "customer-1"})

    now[0] = 15.0
    assert store.consume(ticket) is None
