# Code Map (Bản Đồ Mã Nguồn)

> 🎯 **Mục đích**: Trả lời nhanh câu hỏi *"Muốn sửa X thì mở file nào?"* để Agent không phải quét cả repo.
>
> ⚠️ **TRẠNG THÁI HIỆN TẠI (2026-08-25)**: dự án **chưa có mã nguồn**. `src/` và `tests/` mới chỉ có
> `.gitkeep`. Mục 2 dưới đây là **cấu trúc dự kiến đã chốt**, chưa tồn tại trên đĩa —
> đừng trích dẫn nó như thể đã có. Mỗi khi tạo file thật, chuyển dòng tương ứng sang mục 2 và
> ghi rõ file + hàm.

## 1. Điểm Vào Của Dự Án (Entry Points)

| Loại | Đường dẫn | Trạng thái |
|---|---|---|
| Kho tri thức RAG | `data/knowledge_base/*.md` (7 file) | ✅ Đã có |
| Đặc tả tính năng | `docs/PRD.md` | ✅ Đã có |
| Tập nhãn intent | `docs/intent-taxonomy.md` | ✅ Đã có |
| Backend | `src/backend/main.py` | ⏳ Chưa có (T-009) |
| Frontend | `src/frontend/` (Next.js) | ⏳ Chưa có (T-006) |
| Bộ eval | `eval/run_eval.py` | ⏳ Chưa có (T-008) |
| Biến môi trường | `.env.example` | ⏳ Chưa có (T-009) |

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
| `src/backend/tools/` (sắp có) | Có `idempotency_key` với ràng buộc `UNIQUE` | Đổi cách sinh key = mất tác dụng chống trùng (ADR-005) |

## 5. Nơi KHÔNG Được Sửa Tay

- `node_modules/`, `dist/`, `build/`, `.next/`, `.venv/` — sản phẩm sinh tự động.
- Bảng checkpoint của LangGraph trong DB — do framework quản lý.
