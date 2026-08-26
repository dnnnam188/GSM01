# Code Map (Bản Đồ Mã Nguồn)

> 🎯 **Mục đích**: Trả lời nhanh câu hỏi *"Muốn sửa X thì mở file nào?"* để Agent không phải quét cả repo.
>
> ⚠️ **TRẠNG THÁI (2026-08-26)**: backend hoàn chỉnh về chức năng — LangGraph + 8 tool thật,
> token hoá PII, HITL bằng `interrupt()` + checkpointer Postgres, đã deploy Render + Vercel
> (T-002, T-003, T-004, T-008, T-009, T-010, T-011).
> **Còn lại**: giao diện đầy đủ (T-006), dashboard thống kê (T-014), đo lại & đóng gói (T-012, T-013).
> Bản trên Render đang chạy code **trước T-004** — nhánh `feature/langgraph-agent-tools` chưa merge.

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
| Backend (Windows) | `run_dev.py` | ✅ `.venv/Scripts/python.exe run_dev.py` — **bắt buộc trên Windows**, xem ADR-003 |
| Backend (Linux/Render) | `src/backend/main.py` | ✅ `uvicorn src.backend.main:app` |
| Frontend | `src/frontend/` (Next.js 15) | ✅ `npm run dev` trong `src/frontend/` |
| Cấu hình deploy | `render.yaml`, `requirements.txt`, `docs/DEPLOY.md` | ✅ Sẵn sàng, chưa bấm deploy |
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
| **Một lượt hội thoại** | `src/backend/agent/pipeline.py` → `run_turn()` | T-004 sẽ thay ruột bằng LangGraph, giữ nguyên hợp đồng sự kiện |
| **Viết lại câu hỏi đa lượt** | `src/backend/agent/router.py` → `standalone_query` | Bỏ đi là RAG trả lời sai số liệu, xem bug-history 2026-08-26 |
| Endpoint HTTP + WebSocket | `src/backend/main.py` | `/api/auth/login`, `/api/dashboard/summary`, `/ws/chat` |
| Chặn quyền theo vai trò | `src/backend/main.py` → `require_agent()` | Kiểm ở server, giao diện không phải nơi kiểm |
| Truy vấn DB tầng hội thoại | `src/backend/db/repository.py` | Đồng bộ; API bọc bằng `asyncio.to_thread` |
| Giao diện chat + dashboard | `src/frontend/app/page.tsx` | Bản rút gọn, T-006 làm đầy đủ |
| Sinh idempotency key | `src/backend/tools/contracts.py` → `WriteToolInput.build_idempotency_key()` | Đổi cách sinh = mất tác dụng chống trùng (ADR-005) |
| Nhãn trường PII | `src/backend/tools/contracts.py` → `pii_field()`, `pii_fields_of()` | Tokenizer ở T-010 đọc nhãn này |
| Kết nối DB | `src/backend/db/connection.py` → `get_connection()` | Đọc `DATABASE_URL` từ `.env` |
| **Điều phối agent** | `src/backend/agent/graph.py` → `tool_node()` | Ánh xạ intent→tool bằng luật, không để LLM tự chọn |
| **Điểm dừng HITL** | `src/backend/agent/graph.py` → `interrupt()` trong `tool_node` | Resume chạy LẠI cả node; idempotency chặn trùng (ADR-005) |
| Đánh thức graph | `src/backend/agent/graph.py` → `resume_graph()` | Khoá là `conversation_id` |
| Checkpointer Postgres | `src/backend/agent/checkpointer.py` | Dùng `AsyncConnectionPool`, KHÔNG dùng `from_conn_string` |
| **Thực thi 8 tool** | `src/backend/tools/executor.py` → `execute_tool()` | Điểm vào duy nhất; graph chỉ được gọi qua đây |
| Suy ra quyền hoàn tiền | `src/backend/tools/executor.py` → `derive_refund_evidence()` | Số tiền từ bằng chứng, không từ lời khai (ADR-009) |
| **Token hoá PII** | `src/backend/pii/tokenizer.py` → `tokenize_model()` | Thay theo trường `pii_field()`, không đoán theo mẫu |
| Che PII trên luồng | `src/backend/pii/tokenizer.py` → `StreamMasker` | Che sau vòng lặp là DB sạch mà màn hình bẩn |
| Hàng đợi + duyệt HITL | `src/backend/main.py` → `/api/hitl/queue`, `/api/hitl/{code}/decide` | Ghi DB trước, resume graph sau |
| Đẩy tin về phiên khách | `src/backend/api/hub.py` → `hub.push()` | Trong bộ nhớ; nhiều worker thì phải đổi sang pub/sub |

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
| `src/backend/llm/client.py` → `astream()` | Chính sách thử lại **khác** `generate()`: 429 rơi thẳng sang OpenRouter, không thử lại. Thử lại 3 lần đẩy TTFT lên 12,5 giây | Đừng "thống nhất" hai chính sách này làm một |
| `uvicorn` chạy không có `--reload` | Sửa code xong mà không khởi động lại thì test vẫn chạy code cũ — đã mất một vòng debug vì việc này | Dùng `run_dev.py`, và nhớ khởi động lại sau khi sửa |
| `src/backend/agent/graph.py` → `tool_node` | `interrupt()` khiến node chạy LẠI TỪ ĐẦU khi resume | Mọi tool ghi trong node này phải có idempotency, nếu không mỗi lần duyệt là một bản ghi mới |
| `src/backend/api/hub.py` | Sổ kết nối nằm trong bộ nhớ một tiến trình | Chạy nhiều worker là khách không nhận được kết quả duyệt |

## 5. Nơi KHÔNG Được Sửa Tay

- `node_modules/`, `dist/`, `build/`, `.next/`, `.venv/` — sản phẩm sinh tự động.
- Bảng checkpoint của LangGraph trong DB — do framework quản lý.
