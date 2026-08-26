"""Chốt chặn cấu hình lời gọi LLM.

Vì sao cần: ngày 2026-08-26 một tham số `generationConfig` không hợp lệ
(`thinkingBudget` thay vì `thinkingLevel`) lọt vào `_gemini_body`. Mọi lời gọi
model trả `400 INVALID_ARGUMENT`, agent chỉ còn biết xin lỗi — mà **không một
test nào bắt được**, vì toàn bộ test khác hoặc không gọi model, hoặc coi lỗi model
là chuyện bình thường rồi xuống cấp êm. Chính cơ chế xuống cấp êm đã giấu lỗi đi.

Test này gọi API thật đúng một lần với đúng cái body mà production dùng.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request

import pytest

from src.backend.agent.router import ROUTER_SCHEMA, SYSTEM_PROMPT
from src.backend.llm.client import GEMINI_BASE, LLMClient


def _post(model: str, body: dict) -> int:
    req = urllib.request.Request(
        f"{GEMINI_BASE}/models/{model}:generateContent",
        data=json.dumps(body).encode(),
        headers={"x-goog-api-key": LLMClient().gemini_key, "Content-Type": "application/json"})
    try:
        urllib.request.urlopen(req, timeout=45)
        return 200
    except urllib.error.HTTPError as exc:
        return exc.code


def test_body_that_production_uses_is_accepted_by_gemini():
    """Nếu test này trả 400 thì `generationConfig` có tham số model không nhận."""
    client = LLMClient()
    body = client._gemini_body("phi huy chuyen bao nhieu?", SYSTEM_PROMPT, ROUTER_SCHEMA, 200)
    status = _post(client.router_model, body)
    # Phân biệt rạch ròi: 401/429 là vấn đề của KHOÁ hoặc HẠN MỨC, không phải của
    # cấu hình request — báo đỏ ở đây sẽ đổ oan cho `generationConfig`.
    if status == 429:
        pytest.skip("Chạm hạn mức Gemini — không kết luận được về tính hợp lệ của body")
    if status == 401:
        pytest.skip("GEMINI_API_KEY không hợp lệ hoặc đã bị thu hồi — cấp khoá mới rồi chạy lại")
    assert status == 200, (
        f"Gemini từ chối body của production với HTTP {status}. "
        "Kiểm tra generationConfig: model này nhận `thinkingLevel`, KHÔNG nhận `thinkingBudget`."
    )


def test_generation_config_khong_chua_tham_so_da_biet_la_sai():
    """Chặn ở mức tĩnh, không tốn lời gọi API — chạy được cả khi hết hạn mức."""
    cfg = LLMClient()._gemini_body("x", None, None, 100)["generationConfig"]
    thinking = cfg.get("thinkingConfig", {})
    assert "thinkingBudget" not in thinking, (
        "`thinkingBudget` bị gemini-3.5-flash-* từ chối với 400. Dùng `thinkingLevel`."
    )
    if thinking:
        assert thinking.get("thinkingLevel") in ("low", "high"), thinking


def test_provider_du_phong_cau_hinh_duoc_qua_env(monkeypatch):
    """Đổi provider dự phòng phải là đổi biến môi trường, không phải sửa code.

    Có thêm test này vì đã suýt vấp: bảng `messages` từng có ràng buộc CHECK khoá
    cứng provider vào ('gemini','openrouter'), nên chỉ đổi biến môi trường thôi là
    vỡ ở bước ghi tin nhắn. Ràng buộc đó đã được gỡ.
    """
    import importlib

    monkeypatch.setenv("FALLBACK_BASE_URL", "https://agentrouter.org/v1")
    monkeypatch.setenv("FALLBACK_MODEL", "gpt-5.6-sol")
    monkeypatch.setenv("FALLBACK_PROVIDER_NAME", "agentrouter")
    monkeypatch.setenv("FALLBACK_API_KEY", "sk-test-khong-that")

    from src.backend.llm import client as mod
    importlib.reload(mod)
    try:
        assert mod.FALLBACK_BASE_URL == "https://agentrouter.org/v1"
        assert mod.FALLBACK_MODEL == "gpt-5.6-sol"
        assert mod.FALLBACK_PROVIDER_NAME == "agentrouter"
        assert mod.LLMClient().fallback_key == "sk-test-khong-that"
    finally:
        for var in ("FALLBACK_BASE_URL", "FALLBACK_MODEL",
                    "FALLBACK_PROVIDER_NAME", "FALLBACK_API_KEY"):
            monkeypatch.delenv(var, raising=False)
        importlib.reload(mod)


def test_cot_provider_khong_bi_khoa_cung_vao_danh_sach():
    """Ghi được tên provider bất kỳ thì mới đổi provider bằng cấu hình được."""
    from src.backend.db.connection import get_connection

    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("""SELECT count(*) FROM pg_constraint
                       WHERE conrelid = 'messages'::regclass AND contype = 'c'
                         AND pg_get_constraintdef(oid) ILIKE '%provider%'""")
        assert cur.fetchone()[0] == 0, (
            "messages.provider đang bị ràng buộc CHECK danh sách cứng — "
            "đổi FALLBACK_PROVIDER_NAME sẽ làm vỡ bước ghi tin nhắn."
        )


def test_chuyen_schema_gemini_sang_json_schema_chuan():
    """Không chuyển kiểu thì provider dự phòng tự bịa tên trường và slot rơi hết.

    Đo thực tế trên qwen3.8: gọi không kèm schema cho ra `trip_id`/`item` thay vì
    `ride_code`/`item_description`, khiến agent hỏi lại khách thông tin khách vừa nói.
    """
    from src.backend.agent.router import ROUTER_SCHEMA
    from src.backend.llm.client import _to_json_schema

    converted = _to_json_schema(ROUTER_SCHEMA)
    assert converted["type"] == "object"
    assert converted["properties"]["intent"]["type"] == "string"
    assert converted["properties"]["slots"]["type"] == "object"
    assert converted["properties"]["slots"]["properties"]["ride_code"]["type"] == "string"
    assert converted["properties"]["missing_slots"]["items"]["type"] == "string"
    # enum và required phải giữ nguyên
    assert "booking.cancel" in converted["properties"]["intent"]["enum"]
    assert set(converted["required"]) == set(ROUTER_SCHEMA["required"])


def test_body_du_phong_mang_du_tham_so_rieng_cua_provider(monkeypatch):
    """`reasoning_effort` và sàn max_tokens phải thực sự đi vào request."""
    import importlib

    monkeypatch.setenv("FALLBACK_EXTRA_BODY", '{"reasoning_effort":"low"}')
    monkeypatch.setenv("FALLBACK_MIN_MAX_TOKENS", "800")
    from src.backend.llm import client as mod
    importlib.reload(mod)
    try:
        assert mod.FALLBACK_EXTRA_BODY == {"reasoning_effort": "low"}
        assert mod.FALLBACK_MIN_MAX_TOKENS == 800
        # JSON hỏng thì phải bỏ qua, không được làm sập tiến trình lúc khởi động
        monkeypatch.setenv("FALLBACK_EXTRA_BODY", "{khong-phai-json")
        importlib.reload(mod)
        assert mod.FALLBACK_EXTRA_BODY == {}
    finally:
        for var in ("FALLBACK_EXTRA_BODY", "FALLBACK_MIN_MAX_TOKENS"):
            monkeypatch.delenv(var, raising=False)
        importlib.reload(mod)


def test_rate_limiter_ton_trong_gioi_han_moi_phut():
    """Không gọi API thật — chỉ kiểm phép tính cửa sổ trượt."""
    from src.backend.llm.client import _RateLimiter

    limiter = _RateLimiter(rpm=3)
    # 3 lần đầu đi thẳng
    for _ in range(3):
        assert limiter._wait_seconds("m") == 0.0
    # Lần thứ 4 phải chờ gần trọn một phút
    wait = limiter._wait_seconds("m")
    assert 55.0 < wait <= 60.1, wait
    # Model khác có rổ riêng — đúng như cách Gemini tính hạn mức
    assert limiter._wait_seconds("model-khac") == 0.0
