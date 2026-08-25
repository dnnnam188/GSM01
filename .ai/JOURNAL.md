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
