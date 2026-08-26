# Code Map (Bản Đồ Mã Nguồn)

> 🎯 **Mục đích**: Trả lời nhanh câu hỏi *"Muốn sửa X thì mở file nào?"* để Agent không phải quét cả repo.
>
> ⚠️ **TRẠNG THÁI (2026-08-26)**: đã có tầng dữ liệu, hợp đồng tool, LLM client, RAG,
> router và bộ eval (T-002, T-003, T-008). Tầng LangGraph, API, HITL và giao diện
> **chưa tồn tại** — mục 3 là kế hoạch, đừng trích dẫn như thể đã có.

## 1. Điểm Vào Của Dự Án (Entry Points)

| Loại | Đường dẫn | Trạng thái |
|---|---|---|
| Kho tri thức RAG | `data/knowledge_base/*.md` (7 file) | ✅ Đã có |
| Đặc tả tính năng | `docs/PRD.md` | ✅ Đã có |
| Tập nhãn intent | `docs/intent-taxonomy.md` | ✅ Đã có |
| Schema DB | `src/backend/db/schema.sql` | ✅ Đã có, đã áp lên Neon |
| Seed dữ liệu | `src/backend/db/seed.py` | ✅ Đã có |
| Hợp đồng tool | `src/backend/tools/contracts.py` | ✅ Đã có |
| Tài liệu schema | `docs/DATA-MODEL.md` | ✅ Đã có |
| Backend | `src/backend/main.py` | ⏳ Chưa có (T-009) |
| Frontend | `src/frontend/` (Next.js) | ⏳ Chưa có (T-006) |
| Bộ eval | `eval/run_eval.py` | ✅ Đã có, chạy ra số thật |
| Biến môi trường | `.env.example` | ✅ Đã có |
| Phụ thuộc Python | `pyproject.toml` | ✅ Đã có (`uv`, venv tại `.venv/`) |

## 2. Bản Đồ Tính Năng → Mã Nguồn (đã tồn tại)

| Tính năng / Vùng | Vị trí | Ghi chú |
|---|---|---|
| Chính sách cước & phụ phí | `data/knowledge_base/01_pricing_and_surcharges.md` | Nguồn sự thật cho `fare.inquiry` |
| Chính sách huỷ chuyến | `data/knowledge_base/02_cancellation_and_fees.md` | Dùng khi tính phí trong `cancel_ride` |
| Chính sách hoàn tiền & ngưỡng HITL | `data/knowledge_base/03_refund_and_compensation.md` | **Con số ngưỡng phải đồng bộ với bảng `business_config`** (ADR-006) |
| Quy trình thất lạc đồ | `data/knowledge_base/04_lost_and_found_policy.md` | |
| Chuẩn tài xế & phân cấp khiếu nại | `data/knowledge_base/05_driver_conduct_and_safety.md` | |
| FAQ & tính năng chung | `data/knowledge_base/06_general_faq_and_features.md` | |
| Quy tắc ẩn danh PII | `data/knowledge_base/07_pii_and_privacy_policy.md` | Cơ sở nghiệp vụ của ADR-004 |
| **Định nghĩa 14 bảng** | `src/backend/db/schema.sql` | Ràng buộc `UNIQUE`/`CHECK` là tầng bảo vệ thật, không phải trang trí |
| **Ngưỡng nghiệp vụ** | `src/backend/db/seed.py` → `BUSINESS_CONFIG` | 18 khoá, phải đồng bộ với `data/knowledge_base/` |
| **Case khó cho demo/eval** | `src/backend/db/seed.py` → `CASE_RIDES` | 11 mã chuyến cố định, xem `docs/DATA-MODEL.md` mục 6 |
| **Hợp đồng 8 tool** | `src/backend/tools/contracts.py` → `TOOL_REGISTRY` | Sửa contract phải chạy lại `pytest` |
| **Prompt phân loại intent** | `src/backend/agent/router.py` → `SYSTEM_PROMPT` | Sửa xong **bắt buộc** chạy lại `eval.run_eval --only intent` |
| Gọi LLM + fallback provider | `src/backend/llm/client.py` → `LLMClient.generate()` | Gemini 429/5xx → tự rơi sang OpenRouter |
| Đo TTFT | `src/backend/llm/client.py` → `_gemini_stream()` | Chỉ đo được khi stream, đừng đổi sang gọi non-stream |
| Nhúng vector | `src/backend/llm/client.py` → `LLMClient.embed()` | **Bắt buộc** `outputDimensionality=768` |
| Cắt đoạn kho tri thức | `src/backend/rag/indexer.py` → `chunk_file()` | Cắt theo tiêu đề `##`, không cắt theo độ dài |
| Truy hồi RAG | `src/backend/rag/retriever.py` → `retrieve()` | Dùng `RETRIEVAL_QUERY` cho câu hỏi, `RETRIEVAL_DOCUMENT` cho tài liệu |
| Phát hiện rò rỉ PII | `src/backend/pii/detector.py` → `find_leaks()` | So khớp với PII thật trong DB, không đoán theo mẫu |
| Bộ dữ liệu có nhãn | `eval/datasets/build_datasets.py` | Nhãn gán tay, sửa xong phải chạy lại để sinh `.jsonl` |
| Sinh idempotency key | `src/backend/tools/contracts.py` → `WriteToolInput.build_idempotency_key()` | Đổi cách sinh = mất tác dụng chống trùng (ADR-005) |
| Nhãn trường PII | `src/backend/tools/contracts.py` → `pii_field()`, `pii_fields_of()` | Tokenizer ở T-010 đọc nhãn này |
| Kết nối DB | `src/backend/db/connection.py` → `get_connection()` | Đọc `DATABASE_URL` từ `.env` |

## 3. Cấu Trúc Dự Kiến (chưa tồn tại — kế hoạch)

```text
src/backend/
├── main.py                  # FastAPI app, mount router + WebSocket
├── api/                     # REST: auth, chat, dashboard, hitl
├── agent/
│   ├── graph.py             # Định nghĩa LangGraph, các cạnh rẽ nhánh
│   ├── router.py            # Node phân loại intent (1 lần gọi LLM)
│   ├── nodes/               # rag_node, tool_node, hitl_node, answer_node
│   └── memory.py            # Bộ nhớ 3 tầng
├── tools/                   # book_ride, cancel_ride, request_refund, create_ticket...
├── llm/client.py            # LLMClient: Gemini → OpenRouter fallback (ADR-001)
├── pii/tokenizer.py         # Token hoá PII trước khi vào context (ADR-004)
├── db/                      # models, migrations, seed
└── config/business_config.py # Đọc ngưỡng nghiệp vụ từ DB (ADR-006)

eval/
├── datasets/                # golden_intents.jsonl, rag_qa.jsonl, redteam.jsonl
└── run_eval.py              # In bảng: accuracy · recall@3 · p95 TTFT · token · PII leak
```

## 4. Vùng Nhạy Cảm – Sửa Cẩn Thận ⚠️

| Vị trí | Vì sao nhạy cảm | Cách xử lý an toàn |
|---|---|---|
| `data/knowledge_base/03_*.md` | Chứa ngưỡng hoàn tiền — trùng khái niệm với `business_config` | Sửa một nơi phải đồng bộ nơi kia, nếu không agent trả lời một đằng, hệ thống xử một nẻo |
| `src/backend/pii/tokenizer.py` (sắp có) | Mọi tool đọc dữ liệu đều đi qua đây; hỏng = lộ PII | Sửa xong **bắt buộc** chạy lại bộ red-team trong `eval/` |
| `src/backend/tools/contracts.py` | Có `idempotency_key` với ràng buộc `UNIQUE`; dùng `model_validator` chứ **không** `field_validator` cho ràng buộc liên trường — `field_validator` KHÔNG chạy khi trường vắng mặt | Sửa xong chạy `pytest` |
| `src/backend/db/seed.py` | `TRUNCATE ... CASCADE` — **xoá sạch dữ liệu** mỗi lần chạy | Không chạy trên DB có dữ liệu thật |
| `pyproject.toml` → `requires-python` | Khai báo `>=3.11` nên **không được dùng cú pháp PEP 695** (`class Foo[T]`) | `ruff check` sẽ báo `invalid-syntax` nếu vi phạm |
| `src/backend/agent/router.py` | Prompt này quyết định con số nghiệm thu quan trọng nhất | Đổi một chữ cũng phải đo lại; đừng sửa "cho gọn" |
| `src/backend/rag/indexer.py` | `TRUNCATE knowledge_chunks` mỗi lần chạy, và tốn hạn mức embed | Chỉ chạy lại khi kho tri thức thay đổi |

## 5. Nơi KHÔNG Được Sửa Tay

- `node_modules/`, `dist/`, `build/`, `.next/`, `.venv/` — sản phẩm sinh tự động.
- Bảng checkpoint của LangGraph trong DB — do framework quản lý.
