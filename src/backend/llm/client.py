"""LLMClient — Gemini là chính, OpenRouter là đường lui (ADR-001, ADR-008).

Ba việc lớp này làm mà lời gọi HTTP trần không làm:

1. **Đo TTFT thật.** Ngưỡng "< 3s" của đề bài là thời gian tới *token đầu tiên*,
   không phải thời gian trả xong. Chỉ đo được khi stream, nên `stream_text()`
   ghi lại mốc token đầu tiên và trả về trong `LLMResponse.ttft_ms`.

2. **Chuyển provider khi Gemini hỏng.** 429 (hết hạn mức phút của gói free) và
   5xx đều tự động rơi sang OpenRouter. Đây đồng thời là hạng mục "fallback khi
   lỗi" mà đề bài yêu cầu.

3. **Đếm token.** Mỗi lời gọi trả về `prompt_tokens`/`completion_tokens` để ghi
   vào bảng `messages` và phục vụ cảnh báo hạn mức (F14).
"""
from __future__ import annotations

import json
import os
import random
import time
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(dotenv_path=PROJECT_ROOT / ".env")

GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta"
OPENROUTER_BASE = "https://openrouter.ai/api/v1"

# Ánh xạ sang model tương đương bên OpenRouter khi Gemini không phục vụ được.
OPENROUTER_FALLBACK_MODEL = "google/gemini-2.5-flash-lite"

RETRYABLE_STATUS = {429, 500, 502, 503, 504}


class LLMError(RuntimeError):
    """Cả hai provider đều hỏng. Graph phải trả lời an toàn thay vì văng lỗi."""


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
    router_model: str = field(default_factory=lambda: os.getenv("LLM_ROUTER_MODEL", "gemini-3.5-flash-lite"))
    answer_model: str = field(default_factory=lambda: os.getenv("LLM_ANSWER_MODEL", "gemini-3.5-flash"))
    embedding_model: str = field(
        default_factory=lambda: os.getenv("LLM_EMBEDDING_MODEL", "gemini-embedding-001"))
    embedding_dim: int = field(default_factory=lambda: int(os.getenv("LLM_EMBEDDING_DIM", "768")))
    timeout_s: float = 30.0
    max_attempts: int = 3

    def __post_init__(self) -> None:
        self.gemini_key = os.getenv("GEMINI_API_KEY", "")
        self.openrouter_key = os.getenv("OPENROUTER_API_KEY", "")
        if not self.gemini_key:
            raise RuntimeError("Thiếu GEMINI_API_KEY trong .env")
        self._client = httpx.Client(timeout=self.timeout_s)

    # -- Gemini ------------------------------------------------------------
    def _gemini_body(self, prompt: str, system: str | None, json_schema: dict | None,
                     max_tokens: int) -> dict:
        cfg: dict[str, Any] = {"maxOutputTokens": max_tokens, "temperature": 0.0}
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

    # -- OpenRouter (đường lui) --------------------------------------------
    def _openrouter_call(self, prompt: str, system: str | None, max_tokens: int) -> tuple[str, dict]:
        if not self.openrouter_key:
            raise LLMError("Gemini hỏng và không có OPENROUTER_API_KEY để rơi sang")
        messages = ([{"role": "system", "content": system}] if system else []) + [
            {"role": "user", "content": prompt}]
        resp = self._client.post(
            f"{OPENROUTER_BASE}/chat/completions",
            headers={"Authorization": f"Bearer {self.openrouter_key}"},
            json={"model": OPENROUTER_FALLBACK_MODEL, "messages": messages,
                  "max_tokens": max_tokens, "temperature": 0.0},
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
        """Gọi model, tự thử lại và tự rơi sang OpenRouter khi cần."""
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
                # Backoff có nhiễu ngẫu nhiên: gói free Gemini giới hạn theo phút,
                # thử lại đều nhịp sẽ va vào đúng cửa sổ bị chặn.
                time.sleep(min(2 ** attempt + random.uniform(0, 0.5), 8))
            except (httpx.TimeoutException, httpx.TransportError, LLMError) as exc:
                last_error = exc
                time.sleep(min(2 ** attempt, 8))

        try:
            text, usage = self._openrouter_call(prompt, system, max_tokens)
            return LLMResponse(
                text=text, provider="openrouter", model=OPENROUTER_FALLBACK_MODEL,
                latency_ms=int((time.perf_counter() - started) * 1000),
                prompt_tokens=usage.get("prompt_tokens", 0),
                completion_tokens=usage.get("completion_tokens", 0),
                fell_back=True, attempts=self.max_attempts + 1,
            )
        except Exception as exc:
            raise LLMError(f"Cả Gemini lẫn OpenRouter đều hỏng. Lỗi cuối: {last_error} | {exc}") from exc

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

    def embed(self, texts: list[str], *, task_type: str = "RETRIEVAL_DOCUMENT") -> list[list[float]]:
        """Nhúng nhiều đoạn trong một lời gọi.

        Bắt buộc ép `outputDimensionality`: mặc định model trả 3072 chiều, trong
        khi index HNSW của pgvector chỉ hỗ trợ tối đa 2000 (ADR-008).
        """
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
