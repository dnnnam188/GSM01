"""Cắt đoạn kho tri thức, nhúng vector và nạp vào `knowledge_chunks`.

Chạy: `.venv/Scripts/python.exe -m src.backend.rag.indexer`

Cắt theo tiêu đề `##` thay vì cắt theo số ký tự cố định. Lý do: 7 file trong
`data/knowledge_base/` đều là văn bản chính sách có cấu trúc mục rõ ràng — cắt
mù theo độ dài sẽ chẻ đôi một điều khoản, khiến agent trích dẫn nửa quy định.
Mỗi đoạn được gắn lại tiêu đề file và tiêu đề mục để đứng độc lập vẫn hiểu được.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from src.backend.db.connection import get_connection
from src.backend.llm.client import LLMClient

KB_DIR = Path(__file__).resolve().parents[3] / "data" / "knowledge_base"
MAX_CHARS = 2200  # mục dài hơn mức này bị chẻ tiếp theo ranh giới đoạn văn


@dataclass
class Chunk:
    source_file: str
    heading: str
    chunk_index: int
    content: str


def _split_long(text: str, limit: int = MAX_CHARS) -> list[str]:
    if len(text) <= limit:
        return [text]
    parts: list[str] = []
    buffer: list[str] = []
    size = 0
    for para in text.split("\n\n"):
        if size + len(para) > limit and buffer:
            parts.append("\n\n".join(buffer))
            buffer, size = [], 0
        buffer.append(para)
        size += len(para) + 2
    if buffer:
        parts.append("\n\n".join(buffer))
    return parts


def chunk_file(path: Path) -> list[Chunk]:
    raw = path.read_text(encoding="utf-8")
    lines = raw.splitlines()
    doc_title = next((ln.lstrip("# ").strip() for ln in lines if ln.startswith("# ")), path.stem)

    sections: list[tuple[str, list[str]]] = []
    current_heading = "Phần mở đầu"
    current: list[str] = []
    for line in lines:
        if re.match(r"^##\s+", line):
            if current:
                sections.append((current_heading, current))
            current_heading = line.lstrip("# ").strip()
            current = []
        else:
            current.append(line)
    if current:
        sections.append((current_heading, current))

    chunks: list[Chunk] = []
    index = 0
    for heading, body_lines in sections:
        body = "\n".join(body_lines).strip()
        if len(body) < 40:  # mục rỗng hoặc chỉ có đường kẻ
            continue
        for piece in _split_long(body):
            # Gắn ngữ cảnh vào chính nội dung: đoạn phải tự đứng được khi lọt
            # vào prompt mà không kèm file gốc.
            content = f"[{doc_title}]\n[Mục: {heading}]\n\n{piece}"
            chunks.append(Chunk(path.name, heading, index, content))
            index += 1
    return chunks


def build_chunks() -> list[Chunk]:
    chunks: list[Chunk] = []
    for path in sorted(KB_DIR.glob("*.md")):
        chunks.extend(chunk_file(path))
    return chunks


def index_knowledge_base(batch_size: int = 20) -> dict[str, int]:
    if batch_size <= 0:
        raise ValueError("batch_size phải lớn hơn 0")
    chunks = build_chunks()
    if not chunks:
        raise RuntimeError("Kho tri thức không có chunk nào; không được xoá index hiện tại")
    client = LLMClient()

    vectors: list[list[float]] = []
    for start in range(0, len(chunks), batch_size):
        batch = chunks[start:start + batch_size]
        vectors.extend(client.embed([c.content for c in batch], task_type="RETRIEVAL_DOCUMENT"))

    if len(vectors) != len(chunks):
        raise RuntimeError("Số vector không khớp số chunk; giữ nguyên index hiện tại")
    wrong_dimensions = sorted({len(vector) for vector in vectors if len(vector) != client.embedding_dim})
    if wrong_dimensions:
        raise RuntimeError(
            f"Vector có chiều không đúng: {wrong_dimensions}; cần {client.embedding_dim}"
        )

    with get_connection() as conn, conn.cursor() as cur:
        # TRUNCATE + INSERT nằm trong cùng transaction của get_connection().
        # Nếu insert/commit lỗi, psycopg rollback và index cũ vẫn còn nguyên.
        cur.execute("TRUNCATE knowledge_chunks RESTART IDENTITY")
        cur.executemany(
            "INSERT INTO knowledge_chunks (source_file, heading, chunk_index, content, "
            "token_count, embedding) VALUES (%s, %s, %s, %s, %s, %s)",
            [
                (c.source_file, c.heading, c.chunk_index, c.content,
                 len(c.content) // 4, str(v))
                for c, v in zip(chunks, vectors, strict=True)
            ],
        )
        cur.execute("SELECT count(*) FROM knowledge_chunks")
        loaded = cur.fetchone()[0]
        if loaded != len(chunks):
            raise RuntimeError("Số chunk đã nạp không khớp; rollback index")
    by_file: dict[str, int] = {}
    for c in chunks:
        by_file[c.source_file] = by_file.get(c.source_file, 0) + 1
    return by_file


def main() -> None:
    by_file = index_knowledge_base()
    total = sum(by_file.values())
    print(f"Đã nạp {total} đoạn vào knowledge_chunks:")
    for name, count in sorted(by_file.items()):
        print(f"  {name:45s} {count:>3d} đoạn")


if __name__ == "__main__":
    main()
