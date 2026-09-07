"""LLMClient — Gemini là chính, provider dự phòng tùy chọn (ADR-001, ADR-008).

Ba việc lớp này làm mà lời gọi HTTP trần không làm:

1. **Đo TTFT thật.** Ngưỡng "< 3s" của đề bài là thời gian tới *token đầu tiên*,
   không phải thời gian trả xong. Chỉ đo được khi stream, nên `stream_text()`
   ghi lại mốc token đầu tiên và trả về trong `LLMResponse.ttft_ms`.

2. **Chuyển provider khi Gemini hỏng.** 429 (hết hạn mức phút của gói free) và
   5xx có thể rơi sang provider dự phòng nếu `FALLBACK_ENABLED=true`. Cờ này
   cho phép tắt một provider chưa được kiểm chứng mà không phải sửa luồng Gemini.

3. **Đếm token.** Mỗi lời gọi trả về `prompt_tokens`/`completion_tokens` để ghi
   vào bảng `messages` và phục vụ cảnh báo hạn mức (F14).
"""
from __future__ import annotations

import asyncio
import json
import random
import threading
import time
from collections import defaultdict, deque
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv

from src.backend.config.env import env_int, env_str

PROJECT_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(dotenv_path=PROJECT_ROOT / ".env")

GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta"
FALLBACK_ENABLED = (env_str("FALLBACK_ENABLED", "false") or "").lower() in {
    "1", "true", "yes", "on",
}
# Provider dự phòng cấu hình được hoàn toàn qua .env, miễn là nó theo chuẩn
# OpenAI (`POST {base}/chat/completions`). OpenRouter, AgentRouter, hay bất kỳ
# gateway nào cùng chuẩn đều dùng được mà KHÔNG phải sửa code — bật cờ rồi đổi
# các biến môi trường tương ứng. Khi cờ tắt, không request nào được gửi tới đây.
FALLBACK_BASE_URL = env_str("FALLBACK_BASE_URL", "https://openrouter.ai/api/v1").rstrip("/")
FALLBACK_MODEL = env_str("FALLBACK_MODEL", "google/gemini-2.5-flash-lite")
FALLBACK_PROVIDER_NAME = env_str("FALLBACK_PROVIDER_NAME", "openrouter")

# Tham số riêng của từng provider, truyền dưới dạng JSON trong biến môi trường để
# không phải sửa code mỗi lần đổi nhà cung cấp. Ví dụ với model dòng reasoning:
#   FALLBACK_EXTRA_BODY={"reasoning_effort":"low"}
try:
    FALLBACK_EXTRA_BODY: dict[str, Any] = json.loads(env_str("FALLBACK_EXTRA_BODY", "{}"))
except json.JSONDecodeError:
    FALLBACK_EXTRA_BODY = {}

# Model dòng reasoning tiêu tốn `max_tokens` cho phần suy luận TRƯỚC khi phát ra
# chữ nào. Đo trên qwen3.8: `max_tokens=300` cho ra 301 reasoning token và **0 ký
# tự nội dung**. Sàn này bảo đảm phần suy luận không nuốt hết hạn mức.
FALLBACK_MIN_MAX_TOKENS = env_int("FALLBACK_MIN_MAX_TOKENS", 0)

RETRYABLE_STATUS = {429, 500, 502, 503, 504}

# 400 CỐ Ý không nằm trong danh sách trên. `400 INVALID_ARGUMENT` nghĩa là request
# sai — thử lại hay rơi sang provider khác đều chỉ che mất lỗi cấu hình. Đã mất
# một vòng chẩn đoán vì nhầm 400 với dấu hiệu hết hạn mức, xem bug-history 2026-08-26.
QUOTA_STATUS = {429}

# Số lần thử Gemini trên đường stream tới người dùng trước khi rơi sang fallback.
# Cố tình để thấp: mỗi lần thử lại là một khoản trừ thẳng vào ngân sách 3 giây.
WS_STREAM_MAX_ATTEMPTS = 2



def _to_json_schema(gemini_schema: dict[str, Any]) -> dict[str, Any]:
    """Chuyển schema kiểu Gemini (`"type": "OBJECT"`) sang JSON Schema chuẩn.

    Cần thiết vì provider dự phòng theo chuẩn OpenAI dùng `response_format`, mà
    chuẩn đó đòi tên kiểu viết thường. Không chuyển thì provider dự phòng tự bịa
    tên trường: đo thực tế trên qwen3.8 cho ra `trip_id`/`item` thay vì
    `ride_code`/`item_description`, khiến agent hỏi lại khách thông tin mà khách
    vừa mới nói.
    """
    out: dict[str, Any] = {}
    for key, value in gemini_schema.items():
        if key == "type" and isinstance(value, str):
            out["type"] = value.lower()
        elif key == "properties" and isinstance(value, dict):
            out["properties"] = {k: _to_json_schema(v) for k, v in value.items()}
        elif key == "items" and isinstance(value, dict):
            out["items"] = _to_json_schema(value)
        else:
            out[key] = value
    return out


class _RateLimiter:
    """Cửa sổ trượt theo phút, dùng chung cho cả tiến trình.

    Gói free của Gemini giới hạn **theo phút** cho **từng model**. Trước khi có
    lớp này, bộ eval bắn ~37 lần gọi/phút vào giới hạn 15 — và chỉ sống sót nhờ
    thử lại và rơi sang provider dự phòng, tức là đang lấy cơ chế chịu lỗi ra để
    che một lỗi nhịp độ. Đợi chủ động rẻ hơn nhiều so với ăn 429 rồi thử lại.

    Ghi chú quan trọng: hạn mức tính **theo model**, nên router và bước trả lời
    dùng chung `gemini-3.5-flash-lite` nghĩa là chúng chia nhau CÙNG một rổ 15
    lần/phút — mỗi lượt hội thoại tiêu 2 lần gọi.
    """

    def __init__(self, rpm: int) -> None:
        self.rpm = rpm
        self._calls: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def _wait_seconds(self, key: str) -> float:
        now = time.monotonic()
        window = self._calls[key]
        while window and now - window[0] >= 60.0:
            window.popleft()
        if len(window) < self.rpm:
            window.append(now)
            return 0.0
        return max(0.0, 60.0 - (now - window[0])) + 0.05

    def acquire(self, key: str) -> None:
        while True:
            with self._lock:
                wait = self._wait_seconds(key)
            if wait <= 0:
                return
            time.sleep(wait)

    async def acquire_async(self, key: str) -> None:
        while True:
            with self._lock:
                wait = self._wait_seconds(key)
            if wait <= 0:
                return
            await asyncio.sleep(wait)


GEMINI_RPM = env_int("GEMINI_RPM", 15)
_gemini_limiter = _RateLimiter(GEMINI_RPM)


class LLMError(RuntimeError):
    """Cả hai provider đều hỏng. Graph phải trả lời an toàn thay vì văng lỗi."""


class _StreamHTTPError(Exception):
    """Lỗi HTTP trong lúc stream — mang theo status để quyết định có thử lại không."""

    def __init__(self, status: int, detail: str) -> None:
        super().__init__(f"Gemini {status}: {detail}")
        self.status = status


@dataclass
class LLMResponse:
    text: str
    provider: str
    model: str
    ttft_ms: int | None = None
    latency_ms: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    fell_back: bool = False
    attempts: int = 1

    def as_json(self) -> Any:
        """Đọc kết quả structured output. Gỡ luôn rào ```json nếu model tự thêm."""
        raw = self.text.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]
        return json.loads(raw)


@dataclass
class LLMClient:
    router_model: str = field(default_factory=lambda: env_str("LLM_ROUTER_MODEL", "gemini-3.5-flash-lite"))
    answer_model: str = field(default_factory=lambda: env_str("LLM_ANSWER_MODEL", "gemini-3.5-flash-lite"))
    embedding_model: str = field(
        default_factory=lambda: env_str("LLM_EMBEDDING_MODEL", "gemini-embedding-001"))
    embedding_dim: int = field(default_factory=lambda: env_int("LLM_EMBEDDING_DIM", 768))
    timeout_s: float = 30.0
    max_attempts: int = 3

    def __post_init__(self) -> None:
        self.gemini_key = env_str("GEMINI_API_KEY", "") or ""
        self.fallback_key = env_str("FALLBACK_API_KEY") or env_str("OPENROUTER_API_KEY", "") or ""
        if not self.gemini_key:
            raise RuntimeError("Thiếu GEMINI_API_KEY trong .env")
        self._client = httpx.Client(timeout=self.timeout_s)

    # -- Gemini ------------------------------------------------------------
    def _gemini_body(self, prompt: str, system: str | None, json_schema: dict | None,
                     max_tokens: int) -> dict:
        # `thinkingLevel: "low"` chứ KHÔNG phải `thinkingBudget: 0`.
        # Đo ngày 2026-08-26 trên gemini-3.5-flash-lite: `thinkingBudget` bị từ
        # chối 8/8 lần với `400 INVALID_ARGUMENT`, `thinkingLevel` chạy 8/8 lần.
        cfg: dict[str, Any] = {
            "maxOutputTokens": max_tokens,
            "temperature": 0.0,
            "thinkingConfig": {"thinkingLevel": "low"},
        }
        if json_schema:
            cfg["responseMimeType"] = "application/json"
            cfg["responseSchema"] = json_schema
        body: dict[str, Any] = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": cfg,
        }
        if system:
            body["systemInstruction"] = {"parts": [{"text": system}]}
        return body

    def _gemini_stream(self, model: str, body: dict) -> tuple[str, int | None, dict]:
        _gemini_limiter.acquire(model)
        url = f"{GEMINI_BASE}/models/{model}:streamGenerateContent?alt=sse"
        headers = {"x-goog-api-key": self.gemini_key, "Content-Type": "application/json"}
        chunks: list[str] = []
        ttft_ms: int | None = None
        usage: dict[str, int] = {}
        started = time.perf_counter()
        with self._client.stream("POST", url, json=body, headers=headers) as resp:
            if resp.status_code >= 400:
                resp.read()
                raise httpx.HTTPStatusError(
                    f"Gemini {resp.status_code}: {resp.text[:200]}",
                    request=resp.request, response=resp)
            for line in resp.iter_lines():
                if not line.startswith("data:"):
                    continue
                try:
                    payload = json.loads(line[5:])
                except json.JSONDecodeError:
                    continue
                for cand in payload.get("candidates", []):
                    for part in cand.get("content", {}).get("parts", []):
                        text = part.get("text")
                        if text:
                            if ttft_ms is None:
                                ttft_ms = int((time.perf_counter() - started) * 1000)
                            chunks.append(text)
                if "usageMetadata" in payload:
                    meta = payload["usageMetadata"]
                    usage = {
                        "prompt_tokens": meta.get("promptTokenCount", 0),
                        "completion_tokens": meta.get("candidatesTokenCount", 0),
                    }
        return "".join(chunks), ttft_ms, usage

    # -- Provider dự phòng, chuẩn OpenAI (đường lui) -----------------------
    def _fallback_call(self, prompt: str, system: str | None, max_tokens: int,
                       json_schema: dict | None = None) -> tuple[str, dict]:
        if not FALLBACK_ENABLED:
            raise LLMError(
                "Gemini hỏng; provider dự phòng đang tắt "
                "(FALLBACK_ENABLED=false)")
        if not self.fallback_key:
            raise LLMError(
                "Gemini hỏng và không có khoá provider dự phòng "
                "(FALLBACK_API_KEY hoặc OPENROUTER_API_KEY)")
        messages = ([{"role": "system", "content": system}] if system else []) + [
            {"role": "user", "content": prompt}]
        resp = self._client.post(
            f"{FALLBACK_BASE_URL}/chat/completions",
            headers={"Authorization": f"Bearer {self.fallback_key}"},
            json={"model": FALLBACK_MODEL, "messages": messages,
                  "max_tokens": max(max_tokens, FALLBACK_MIN_MAX_TOKENS),
                  "temperature": 0.0,
                  **({"response_format": {"type": "json_schema", "json_schema": {
                      "name": "structured_output", "strict": False,
                      "schema": _to_json_schema(json_schema)}}} if json_schema else {}),
                  **FALLBACK_EXTRA_BODY},
        )
        resp.raise_for_status()
        data = resp.json()
        usage = data.get("usage", {})
        return data["choices"][0]["message"]["content"], {
            "prompt_tokens": usage.get("prompt_tokens", 0),
            "completion_tokens": usage.get("completion_tokens", 0),
        }

    # -- API công khai ------------------------------------------------------
    def generate(self, prompt: str, *, system: str | None = None, model: str | None = None,
                 json_schema: dict | None = None, max_tokens: int = 1024) -> LLMResponse:
        """Gọi model, tự thử lại và rơi sang fallback nếu được bật."""
        model = model or self.answer_model
        body = self._gemini_body(prompt, system, json_schema, max_tokens)
        started = time.perf_counter()
        last_error: Exception | None = None

        for attempt in range(1, self.max_attempts + 1):
            try:
                text, ttft_ms, usage = self._gemini_stream(model, body)
                if not text.strip():
                    raise LLMError("Gemini trả về nội dung rỗng")
                return LLMResponse(
                    text=text, provider="gemini", model=model, ttft_ms=ttft_ms,
                    latency_ms=int((time.perf_counter() - started) * 1000),
                    prompt_tokens=usage.get("prompt_tokens", 0),
                    completion_tokens=usage.get("completion_tokens", 0),
                    attempts=attempt,
                )
            except httpx.HTTPStatusError as exc:
                last_error = exc
                status = exc.response.status_code if exc.response else 0
                if status not in RETRYABLE_STATUS:
                    break
                if status in QUOTA_STATUS:
                    break  # hết hạn mức thì thử lại vô ích, rơi sang dự phòng ngay

                # Backoff có nhiễu ngẫu nhiên: gói free Gemini giới hạn theo phút,
                # thử lại đều nhịp sẽ va vào đúng cửa sổ bị chặn.
                time.sleep(min(2 ** attempt + random.uniform(0, 0.5), 8))
            except (httpx.TimeoutException, httpx.TransportError, LLMError) as exc:
                last_error = exc
                time.sleep(min(2 ** attempt, 8))

        try:
            text, usage = self._fallback_call(prompt, system, max_tokens, json_schema)
            return LLMResponse(
                text=text, provider=FALLBACK_PROVIDER_NAME, model=FALLBACK_MODEL,
                latency_ms=int((time.perf_counter() - started) * 1000),
                prompt_tokens=usage.get("prompt_tokens", 0),
                completion_tokens=usage.get("completion_tokens", 0),
                fell_back=True, attempts=self.max_attempts + 1,
            )
        except Exception as exc:
            fallback_state = "đang tắt" if not FALLBACK_ENABLED else "không phản hồi"
            raise LLMError(
                f"Gemini lỗi và đường fallback {fallback_state}. "
                f"Lỗi cuối: {last_error} | {exc}") from exc

    def stream_text(self, prompt: str, *, system: str | None = None,
                    model: str | None = None, max_tokens: int = 1024) -> Iterator[str]:
        """Stream cho giao diện chat. Dùng ở T-009."""
        model = model or self.answer_model
        body = self._gemini_body(prompt, system, None, max_tokens)
        url = f"{GEMINI_BASE}/models/{model}:streamGenerateContent?alt=sse"
        headers = {"x-goog-api-key": self.gemini_key, "Content-Type": "application/json"}
        with self._client.stream("POST", url, json=body, headers=headers) as resp:
            resp.raise_for_status()
            for line in resp.iter_lines():
                if not line.startswith("data:"):
                    continue
                try:
                    payload = json.loads(line[5:])
                except json.JSONDecodeError:
                    continue
                for cand in payload.get("candidates", []):
                    for part in cand.get("content", {}).get("parts", []):
                        if part.get("text"):
                            yield part["text"]


    async def _astream_gemini(self, model: str, body: dict, started: float, emitted: list[bool]):
        await _gemini_limiter.acquire_async(model)
        url = f"{GEMINI_BASE}/models/{model}:streamGenerateContent?alt=sse"
        headers = {"x-goog-api-key": self.gemini_key, "Content-Type": "application/json"}
        async with httpx.AsyncClient(timeout=self.timeout_s) as http:
            async with http.stream("POST", url, json=body, headers=headers) as resp:
                if resp.status_code >= 400:
                    await resp.aread()
                    raise _StreamHTTPError(resp.status_code, resp.text[:200])
                async for line in resp.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    try:
                        payload = json.loads(line[5:])
                    except json.JSONDecodeError:
                        continue
                    for cand in payload.get("candidates", []):
                        for part in cand.get("content", {}).get("parts", []):
                            text = part.get("text")
                            if text:
                                ttft = None
                                if not emitted[0]:
                                    ttft = int((time.perf_counter() - started) * 1000)
                                    emitted[0] = True
                                yield text, ttft, None
                    if "usageMetadata" in payload:
                        meta = payload["usageMetadata"]
                        yield "", None, {
                            "provider": "gemini",
                            "model": model,
                            "prompt_tokens": meta.get("promptTokenCount", 0),
                            "completion_tokens": meta.get("candidatesTokenCount", 0),
                        }

    async def _astream_fallback(self, prompt: str, system: str | None, max_tokens: int,
                                  started: float, emitted: list[bool]):
        if not FALLBACK_ENABLED:
            raise LLMError(
                "Gemini hỏng; provider dự phòng đang tắt "
                "(FALLBACK_ENABLED=false)")
        if not self.fallback_key:
            raise LLMError(
                "Gemini hỏng và không có khoá provider dự phòng "
                "(FALLBACK_API_KEY hoặc OPENROUTER_API_KEY)")
        messages = ([{"role": "system", "content": system}] if system else []) + [
            {"role": "user", "content": prompt}]
        payload = {"model": FALLBACK_MODEL, "messages": messages,
                   "max_tokens": max(max_tokens, FALLBACK_MIN_MAX_TOKENS),
                   "temperature": 0.0, "stream": True,
                   "stream_options": {"include_usage": True}, **FALLBACK_EXTRA_BODY}
        headers = {"Authorization": f"Bearer {self.fallback_key}"}
        async with httpx.AsyncClient(timeout=self.timeout_s) as http:
            async with http.stream("POST", f"{FALLBACK_BASE_URL}/chat/completions",
                                   json=payload, headers=headers) as resp:
                if resp.status_code >= 400:
                    await resp.aread()
                    raise LLMError(f"OpenRouter {resp.status_code}: {resp.text[:200]}")
                async for line in resp.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    chunk = line[5:].strip()
                    if chunk == "[DONE]":
                        break
                    try:
                        data = json.loads(chunk)
                    except json.JSONDecodeError:
                        continue
                    for choice in data.get("choices", []):
                        text = (choice.get("delta") or {}).get("content")
                        if text:
                            ttft = None
                            if not emitted[0]:
                                ttft = int((time.perf_counter() - started) * 1000)
                                emitted[0] = True
                            yield text, ttft, None
                    if data.get("usage"):
                        yield "", None, {
                            "provider": FALLBACK_PROVIDER_NAME,
                            "model": FALLBACK_MODEL,
                            "prompt_tokens": data["usage"].get("prompt_tokens", 0),
                            "completion_tokens": data["usage"].get("completion_tokens", 0),
                        }

    async def astream(self, prompt: str, *, system: str | None = None,
                      model: str | None = None, max_tokens: int = 1024):
        """Stream bất đồng bộ cho WebSocket, có thử lại và có đường lui tùy chọn.

        Yield tuple (text_delta, ttft_ms, usage). `ttft_ms` chỉ khác None ở đúng
        mảnh đầu tiên — đó là con số dùng nghiệm thu ngưỡng 3 giây.

        Quy tắc then chốt: **chỉ được thử lại khi CHƯA phát ra token nào**. Nếu
        luồng đứt giữa chừng, gọi lại sẽ sinh ra câu trả lời chắp vá hai nửa
        khác nhau — với khách hàng thì đó còn tệ hơn là một câu xin lỗi.
        """
        model = model or self.answer_model
        body = self._gemini_body(prompt, system, None, max_tokens)
        started = time.perf_counter()
        emitted = [False]
        last_error: Exception | None = None

        # Đường người dùng thật chỉ có ngân sách 3 giây, nên chính sách thử lại ở
        # đây KHÁC với `generate()` (dùng cho eval, nơi độ trễ không quan trọng):
        #   429 -> rơi thẳng sang OpenRouter, KHÔNG thử lại. Hạn mức không hồi
        #          lại trong vài giây; thử lại chỉ đốt sạch ngân sách độ trễ rồi
        #          vẫn hỏng. Đo thực tế: thử lại 3 lần đẩy TTFT lên 12,5 giây.
        #   5xx / timeout -> thử lại đúng MỘT lần rồi mới rơi.
        for _attempt in range(1, WS_STREAM_MAX_ATTEMPTS + 1):
            try:
                async for item in self._astream_gemini(model, body, started, emitted):
                    yield item
                return
            except _StreamHTTPError as exc:
                last_error = exc
                quota_exhausted = exc.status in QUOTA_STATUS
                if emitted[0] or quota_exhausted or exc.status not in RETRYABLE_STATUS:
                    break
                await asyncio.sleep(0.3 + random.uniform(0, 0.2))
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                last_error = exc
                if emitted[0]:
                    break
                await asyncio.sleep(0.3)

        if emitted[0]:
            raise LLMError(f"Luồng đứt sau khi đã phát token: {last_error}")

        async for item in self._astream_fallback(prompt, system, max_tokens, started, emitted):
            yield item

    def embed(self, texts: list[str], *, task_type: str = "RETRIEVAL_DOCUMENT") -> list[list[float]]:
        """Nhúng nhiều đoạn trong một lời gọi.

        Bắt buộc ép `outputDimensionality`: mặc định model trả 3072 chiều, trong
        khi index HNSW của pgvector chỉ hỗ trợ tối đa 2000 (ADR-008).
        """
        _gemini_limiter.acquire(self.embedding_model)
        url = f"{GEMINI_BASE}/models/{self.embedding_model}:batchEmbedContents"
        headers = {"x-goog-api-key": self.gemini_key, "Content-Type": "application/json"}
        requests = [
            {
                "model": f"models/{self.embedding_model}",
                "content": {"parts": [{"text": t}]},
                "taskType": task_type,
                "outputDimensionality": self.embedding_dim,
            }
            for t in texts
        ]
        last_error: Exception | None = None
        for attempt in range(1, self.max_attempts + 1):
            resp = self._client.post(url, json={"requests": requests}, headers=headers)
            if resp.status_code in RETRYABLE_STATUS:
                last_error = httpx.HTTPStatusError(
                    f"embed {resp.status_code}", request=resp.request, response=resp)
                time.sleep(min(2 ** attempt + random.uniform(0, 0.5), 10))
                continue
            resp.raise_for_status()
            return [e["values"] for e in resp.json()["embeddings"]]
        raise LLMError(f"Nhúng thất bại sau {self.max_attempts} lần: {last_error}")
