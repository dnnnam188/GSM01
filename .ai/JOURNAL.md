# JOURNAL – Nhật Ký Bàn Giao Ca

> 🎯 **Mục đích**: Trả lời câu hỏi *"ĐÃ XẢY RA CHUYỆN GÌ?"* — file này là **nhật ký, chỉ thêm mới**.
> Việc *còn phải làm gì* nằm ở `.ai/TASKS.md`, đừng gộp hai thứ vào đây.
>
> 📋 **Định dạng**: dùng mẫu tại `.ai/templates/journal-entry.md`.
> 🔝 **Thứ tự**: entry mới nhất đặt **trên cùng**.
> 🔄 **Khi nào ghi**: cuối mỗi phiên làm việc, hoặc khi hoàn thành một task lớn.
>
> 👉 **Agent mới vào phiên**: đọc 3–5 entry gần nhất là đủ, không cần đọc hết file.

---

<!-- Thêm entry mới ngay dưới dòng này -->

## [2026-08-26] – D2: Tầng Dữ Liệu Trên Neon & Hợp Đồng 8 Tool

- **Agent / Người thực hiện**: Claude Code
- **Task liên quan**: T-002 ✅, T-003 ✅ · phát sinh ADR-008

### ✅ Đã làm được

**Đo thực tế trước khi chốt (thay vì tin trí nhớ)** — phần giá trị nhất của phiên này:
- Gọi API list-models bằng key thật: `gemini-2.5-flash` và `gemini-2.5-flash-lite` trả
  **HTTP 404 "no longer available to new users"**. Nếu hardcode theo tài liệu phổ biến thì
  toàn bộ dự án đã hỏng ngay ở D4.
- Đo TTFT bằng streaming SSE, mỗi model 2 lần. Kết quả **ngược với trực giác**:
  `gemini-3.5-flash-lite` 0,86–0,96s · `gemini-3.5-flash` 2,04–2,07s ·
  `gemini-3.6-flash` 5,10–5,94s · `gemini-3.7-flash` **timeout >30s** ·
  `gemini-flash-latest` **timeout >30s**.
  → **Model mới hơn chậm hơn nhiều lần.** Chọn theo số hiệu phiên bản là phá ngưỡng 3 giây.
- Đo chiều embedding: `gemini-embedding-001` mặc định trả **3072**, ép được xuống **768**.
  Quan trọng vì index HNSW của pgvector chỉ hỗ trợ tối đa 2000 chiều.
- → Ghi **ADR-008**: ghim `gemini-3.5-flash-lite` cho router, `gemini-3.5-flash` cho trả lời,
  cấm dùng alias `-latest` ở mọi nơi.

**T-002 — Tầng dữ liệu (đã áp lên Neon thật, không phải localhost)**:
- Neon PostgreSQL 17.11, `pgvector` 0.8.0, vùng `ap-southeast-1`.
- **14 bảng** (nhiều hơn 12 dự kiến — tách `ride_events`, `payments`, `knowledge_chunks`,
  `csat_ratings` thành bảng riêng thay vì nhồi vào JSONB).
- Ràng buộc đẩy xuống tầng DB, **đã thử phá và DB chặn thật**:
  - ghi trùng `idempotency_key` → `duplicate key value violates unique constraint` ✅
  - `REJECTED` mà không có lý do → `violates check constraint refund_reject_needs_reason` ✅
- Seed tất định (`random.Random(42)`): 52 người dùng, 20 tài xế, **311 chuyến**,
  18 khoá `business_config` đối soát từ `data/knowledge_base/`.
- **11 case khó có `ride_code` cố định**, trong đó 3 cặp có/không đủ điều kiện
  (`DOUBLE-01`/`02`, `DETOUR-01`/`02`, `CANCELFEE-01`/`02`) — dùng để kiểm tra agent
  **từ chối đúng**, không chỉ đồng ý đúng.
- 4 truy vấn kiểm chứng chạy thật: lọc đúng `XSM-DETOUR-01` (+61,5%) và loại đúng
  `XSM-DETOUR-02` (+13,9%); lọc đúng `XSM-CANCELFEE-01` (giây 74) và loại `-02` (phút 6).

**T-003 — Hợp đồng 8 tool**:
- 5 tool ghi / 3 tool đọc, `extra="forbid"` để LLM bịa tham số là fail sớm.
- `ToolErrorType` 3 nhánh `RETRYABLE / FATAL / NEEDS_HUMAN` — quyết định graph thử lại,
  bỏ cuộc, hay `interrupt()`.
- Trường PII đánh dấu bằng `pii_field()`, đọc lại bằng `pii_fields_of()` — tokenizer ở T-010 dùng.
- 11 test pass, `ruff` sạch.

### 🐞 Hai lỗi thật do test bắt được (không phải test cho có)
1. **`field_validator` không chạy khi trường vắng mặt.** `create_ticket` thiếu `ride_code` và
   `modify_ride` gọi rỗng đều **lọt qua validation**. Phải đổi sang `model_validator(mode="after")`.
   Đây đúng là lỗi LLM hay tạo ra nhất: gọi tool với payload thiếu.
2. **`class ToolResult[T]` là cú pháp PEP 695, chỉ chạy từ Python 3.12**, trong khi
   `pyproject.toml` khai báo `requires-python >=3.11`. `ruff` bắt được `invalid-syntax`.
   Đã đổi sang `Generic[T]`. Nếu để nguyên thì vỡ lúc deploy lên Render.

### 📁 File đã thay đổi
- `src/backend/db/schema.sql` — **mới**, 14 bảng + ràng buộc + index HNSW
- `src/backend/db/connection.py`, `apply_schema.py`, `seed.py` — **mới**
- `src/backend/tools/contracts.py` — **mới**, 8 tool + error taxonomy + `TOOL_REGISTRY`
- `tests/test_tool_contracts.py` — **mới**, 11 test
- `pyproject.toml`, `.env.example` — **mới**
- `docs/DATA-MODEL.md` — **mới**, tài liệu 14 bảng + 11 case khó + truy vấn kiểm chứng
- `.ai/context/decisions.md` — thêm ADR-008
- `.ai/context/codemap.md`, `.ai/rules/definition-of-done.md`, `.ai/TASKS.md` — cập nhật

### ⏳ Đang dở
- Không. T-002 và T-003 đã thoả DoD → chuyển ✅.

### ⚠️ Vướng mắc / Cần con người quyết
- `uv run` **không dùng được** trên máy này: nó nhắm vào Python toàn cục ở `C:\Program Files`
  và lỗi `Access is denied`. Đã chuyển sang gọi thẳng `.venv/Scripts/python.exe` và ghi vào DoD.
- Chưa kiểm chứng: chưa gọi thử tool nào thật (mới chỉ có contract, chưa có phần thực thi),
  chưa index kho tri thức vào `knowledge_chunks`.
- ⚠️ Nhắc cho D3: gói free của Gemini có giới hạn theo phút. Bộ eval 130 câu chạy liên tiếp
  rất dễ dính 429 — phải có nghỉ giữa các lần gọi và cache kết quả embedding.

### ➡️ Việc tiếp theo
- **D3 (T-008) — Eval harness. Đây là task không được cắt.**
  - 80 câu intent có nhãn, phủ đủ 9 dạng đầu vào ở `docs/intent-taxonomy.md` mục 3
    (không dấu, teencode, sai chính tả, trộn Anh–Việt, cảm xúc mạnh, cực ngắn, nhiều ý,
    ngoài phạm vi, prompt injection).
  - 30 câu RAG ↔ đoạn KB đúng; 20 prompt red-team PII.
  - `eval/run_eval.py` in bảng 5 chỉ số: intent accuracy · recall@3 · p95 TTFT · token/lượt · PII leak.
  - Dùng 11 `ride_code` cố định trong `docs/DATA-MODEL.md` mục 6 làm dữ liệu cho câu hỏi.

---

## [2026-08-25] – D1: Đóng Băng Đặc Tả, Chốt 7 ADR & Tái Cấu Trúc Sprint 13 Ngày

- **Agent / Người thực hiện**: Claude Code
- **Task liên quan**: T-007 (mới mở) · T-001 (đóng ✅)

### ✅ Đã làm được
- **Chẩn đoán backlog cũ**: T-002→T-006 đi thẳng từ kho tri thức sang code, thiếu lớp đặc tả và lớp
  đo lường. Hệ quả nếu giữ nguyên: có agent chạy được nhưng **không chứng minh được** ba ràng buộc
  cứng của đề bài (intent ≥ 90%, phản hồi < 3s, không rò PII).
- **Chốt lộ trình 13 ngày** (25/08 → 06/09) với 7 mốc M1–M7, kèm quy tắc chống trượt tiến độ:
  trễ thì cắt scope P1/P2 của chính mốc đó, không lấn sang ngày của mốc sau.
- **Viết `docs/PRD.md` thật** thay template: 2 persona, 16 tính năng F01–F16 với tiêu chí nghiệm thu
  kiểm chứng được, bảng ràng buộc phi chức năng, và mục "ngoài phạm vi" để chặn scope creep.
- **Viết `docs/intent-taxonomy.md`**: khoá cứng **10 nhãn**, kèm bảng 12 ranh giới dễ nhầm và quy tắc
  ưu tiên khi một câu chứa nhiều ý. Chốt gộp smalltalk + ngoài-phạm-vi vào `other` vì hai loại này
  khác nhau ở câu trả lời chứ không khác ở hành động.
- **Chốt 7 ADR** — ba quyết định đáng chú ý nhất:
  - ADR-004: PII **token hoá trước khi vào context LLM** (`0912345678` → `<PHONE_C7>`), regex lọc đầu
    ra chỉ là lưới lớp hai. Lý do: LLM không thể làm lộ thứ nó chưa từng nhìn thấy.
  - ADR-005: mọi tool ghi dữ liệu có `idempotency_key` ràng buộc `UNIQUE` ở tầng DB — tầng bảo vệ duy
    nhất không phụ thuộc vào việc LLM cư xử đúng.
  - ADR-003: HITL bằng `interrupt()` + checkpointer Postgres, để hội thoại **chạy tiếp** sau khi CSKH
    duyệt, thay vì "tạo ticket rồi kết thúc".
- **Viết `.ai/context/architecture.md`** (trước đó là file rỗng 0 dòng): sơ đồ tổng thể, vòng đời một
  lượt hội thoại, ba tầng bảo vệ, bộ nhớ 3 tầng và **bảng ngân sách độ trễ** cho ngưỡng TTFT < 3s.
- **Bổ sung DoD đặc thù LLM**: đụng vào agent/prompt/RAG thì bắt buộc chạy lại bộ eval và dán 3 con số
  vào JOURNAL — "chạy thử thấy đúng vài câu" không được tính là bằng chứng.

### 📁 File đã thay đổi
- `docs/PRD.md` — viết mới hoàn toàn (F01–F16 + ràng buộc + ngoài phạm vi)
- `docs/intent-taxonomy.md` — **file mới**, 10 nhãn + ranh giới nhầm lẫn
- `.ai/context/decisions.md` — thêm ADR-001…007
- `.ai/context/architecture.md` — viết mới (trước đó rỗng)
- `.ai/context/project-overview.md` — thay toàn bộ placeholder
- `.ai/context/glossary.md` — thay toàn bộ placeholder
- `.ai/context/codemap.md` — ghi rõ cái gì đã có / chưa có, thêm cảnh báo `index.html` 833KB
- `.ai/rules/definition-of-done.md` — thêm checklist LLM & tool, điền mục 3 "Dự án này"
- `.ai/rules/coding-style.md` — tách quy ước đặt tên theo ngôn ngữ (ADR-007)
- `.ai/TASKS.md` — tái cấu trúc theo sprint 13 ngày, T-001 → ✅, mở T-007…T-015

### ⏳ Đang dở
- Không. T-007 đã thoả toàn bộ tiêu chí nghiệm thu → chuyển ✅.
- `README.md` vẫn còn là template ("Tên Dự Án") — cố ý để lại, thuộc phạm vi T-013 (D13).

### ⚠️ Vướng mắc / Cần con người quyết
- **Chưa kiểm chứng được** bất cứ điều gì bằng cách chạy thử: phiên này chỉ tạo tài liệu, chưa có mã
  nguồn, chưa có DB, chưa có key nào được nạp. Đúng theo mục 4 của DoD.
- Cần người dùng xác nhận trước D2: chọn **Neon** hay **Supabase** cho Postgres, và tạo sẵn
  `.env` chứa `GEMINI_API_KEY` + `OPENROUTER_API_KEY` (không commit — xem `.ai/rules/security.md`).
- ID model Gemini Flash cụ thể phải lấy bằng lệnh list-models với key thật ở D2, **không hardcode**.

### ➡️ Việc tiếp theo
- **D2 (T-002 + T-003)**: viết DDL 12 bảng — trong đó `tool_calls` (có `idempotency_key UNIQUE`),
  `audit_log`, `business_config` là bảng hạng nhất, không phải log file. Seed 50 khách / 300 chuyến
  **có cài sẵn 4 case khó**: thu tiền trùng, lộ trình đi vòng >30%, huỷ trong 2 phút, bỏ quên đồ.
  Song song: 8 Pydantic tool contract kèm error taxonomy `RETRYABLE / FATAL / NEEDS_HUMAN`.

## [2026-08-25] – Khởi tạo & Đối Soát Bộ Tri thức RAG Với Dữ Liệu Thực Tế Xanh SM
- **Agent / Người thực hiện**: Antigravity
- **Task liên quan**: T-001

### ✅ Đã làm được
- Thực hiện Search Web tra cứu thông tin niêm yết chính thức từ `xanhsm.com`, `greensm.com` và các kênh truyền thông chính thống.
- Cập nhật số liệu chuẩn xác 100% cho biểu phí: Xanh SM Bike (13.800đ/2km đầu, 4.800đ/km tiếp), GreenCar VF 5/e34 (30.500đ/2km đầu, 15.500đ/km tiếp), Luxury VF 8 (21.000đ/km), phụ phí đêm 22h-6h (10k/20k), phí chờ (60.000đ/h), phí thêm điểm dừng (10.000đ/điểm), Hotline 24/7 (1900 2088), email `support.vn@greensm.com`.
- Hoàn thiện trọn bộ 7 tài liệu Markdown chuẩn RAG trong `data/knowledge_base/`.

### 📁 File đã tạo
- `data/knowledge_base/01_pricing_and_surcharges.md` — Biểu phí & phụ phí chi tiết 3 dòng xe (Bike, GreenCar, Luxury)
- `data/knowledge_base/02_cancellation_and_fees.md` — Chính sách hủy chuyến, điều kiện miễn phí & phí No-Show
- `data/knowledge_base/03_refund_and_compensation.md` — Chính sách hoàn tiền, ngưỡng AI Auto-Refund vs CSKH HITL
- `data/knowledge_base/04_lost_and_found_policy.md` — Quy trình tìm kiếm đồ thất lạc và bảo mật SĐT
- `data/knowledge_base/05_driver_conduct_and_safety.md` — Chuẩn 5 sao và 3 cấp độ xử lý khiếu nại tài xế
- `data/knowledge_base/06_general_faq_and_features.md` — Hướng dẫn đặt đa điểm, đặt hộ, thú cưng, VAT e-invoice
- `data/knowledge_base/07_pii_and_privacy_policy.md` — Quy tắc ẩn danh PII và quy định bảo mật dữ liệu

### ⏳ Đang dở
- Task T-002: Thiết kế Database Schema (PostgreSQL) và Mock Seed Data.

### ⚠️ Vướng mắc / Cần con người quyết
- Không.

### ➡️ Việc tiếp theo
- Thiết kế Data Schema (PostgreSQL DDL) và Pydantic Schemas cho các Tool Function (T-002, T-003).
