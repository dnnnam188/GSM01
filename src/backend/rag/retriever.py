"""Truy hồi đoạn tri thức bằng cosine similarity trên pgvector."""
from __future__ import annotations

from dataclasses import dataclass

from src.backend.db.connection import get_connection
from src.backend.llm.client import LLMClient


@dataclass
class RetrievedChunk:
    source_file: str
    heading: str
    content: str
    similarity: float


def retrieve(query: str, top_k: int = 3, client: LLMClient | None = None) -> list[RetrievedChunk]:
    """Trả về top_k đoạn gần nhất.

    `task_type="RETRIEVAL_QUERY"` chứ không phải RETRIEVAL_DOCUMENT: gemini-embedding
    nhúng câu hỏi và tài liệu vào hai không gian hơi khác nhau, dùng sai loại sẽ
    làm tụt recall mà không báo lỗi gì.
    """
    client = client or LLMClient()
    vector = client.embed([query], task_type="RETRIEVAL_QUERY")[0]
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT source_file, heading, content, 1 - (embedding <=> %s::vector) AS similarity "
            "FROM knowledge_chunks ORDER BY embedding <=> %s::vector LIMIT %s",
            (str(vector), str(vector), top_k),
        )
        return [RetrievedChunk(*row) for row in cur.fetchall()]
