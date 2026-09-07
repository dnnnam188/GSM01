from __future__ import annotations

from fastapi.testclient import TestClient

from src.backend import main


def test_websocket_authenticates_with_one_time_ticket_without_llm(monkeypatch):
    async def fake_run_turn(*_args, **_kwargs):
        yield {"type": "token", "value": "Xin chào"}
        yield {"type": "done", "intent": "other", "ttft_ms": 1, "degraded": False}

    async def noop(*_args, **_kwargs):
        return None

    monkeypatch.setattr(main, "run_turn", fake_run_turn)
    monkeypatch.setattr(main.repo, "get_or_create_conversation", lambda *_args: "conversation-test")
    monkeypatch.setattr(main.hub, "register", noop)
    monkeypatch.setattr(main.hub, "unregister", noop)
    ticket, _ = main._ws_tickets.issue({
        "id": "customer-test",
        "email": "customer@example.com",
        "role": "customer",
    })

    with TestClient(main.app) as client:
        with client.websocket_connect(
            "/ws/chat",
            headers={"origin": "http://localhost:3000"},
        ) as websocket:
            websocket.send_json({"type": "auth", "ticket": ticket})
            assert websocket.receive_json()["type"] == "ready"
            websocket.send_json({"message": "xin chào"})
            assert websocket.receive_json() == {"type": "token", "value": "Xin chào"}
            assert websocket.receive_json()["type"] == "done"


def test_websocket_rejects_access_token_sent_as_ticket():
    with TestClient(main.app) as client:
        with client.websocket_connect(
            "/ws/chat",
            headers={"origin": "http://localhost:3000"},
        ) as websocket:
            websocket.send_json({"type": "auth", "ticket": "jwt.long-lived-token"})
            error = websocket.receive_json()
            assert error["type"] == "error"
            assert "Ticket" in error["value"]
