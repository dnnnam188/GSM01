# TASKS – Bảng Công Việc

> 🎯 **Mục đích**: Nguồn duy nhất trả lời câu hỏi *"CÒN GÌ PHẢI LÀM?"*.
> Phân biệt rõ với `JOURNAL.md` — JOURNAL ghi *đã xảy ra chuyện gì* (nhật ký, chỉ thêm mới),
> còn TASKS ghi *còn phải làm gì* (file sống, sửa liên tục).

## Quy Ước Trạng Thái
| Ký hiệu | Ý nghĩa |
|---|---|
| ⏳ | Đang làm dở (Work In Progress) |
| ☐ | Chưa bắt đầu (Backlog) |
| ✅ | Đã hoàn thành & đã nghiệm thu |
| ❄️ | Tạm hoãn / chờ quyết định của con người |

**Mức ưu tiên**: `P0` = bắt buộc, chặn việc khác · `P1` = quan trọng · `P2` = mở rộng, nice-to-have.

## Quy Tắc Bắt Buộc Cho AI Agent
1. Đầu phiên: đọc mục **⏳ Đang Dở** trước tiên, cầm tiếp việc ở đó thay vì tự mở việc mới.
2. Khi bắt đầu một task: chuyển từ `☐` sang `⏳` **ngay lập tức**, ghi rõ agent nào đang cầm.
3. Khi xong: chỉ được chuyển sang `✅` khi đã thỏa `.ai/rules/definition-of-done.md`.
4. Không xóa task đã xong — chuyển xuống mục **✅ Đã Xong** để giữ dấu vết.
5. Mục ⏳ nên giữ tối đa 1–2 task. Nhiều hơn nghĩa là đang làm dàn trải.

---

## 🗓️ Lịch Sprint 13 Ngày (2026-08-25 → 2026-09-06)

| Ngày | Mốc | Task |
|---|---|---|
| D1 · 25/08 | M1 Đặc tả đóng băng | T-007 |
| D2 · 26/08 | M2 Hợp đồng dữ liệu | T-002, T-003 |
| D3 · 27/08 | M3 Bộ eval chạy được | T-008 |
| D4–D5 · 28–29/08 | M4 Vertical slice **đã deploy** | T-009 |
| D6–D8 · 30/08–01/09 | M5 Agent đầy đủ | T-004, T-010, T-011 |
| D9–D11 · 02–04/09 | M6 Giao diện | T-005, T-006 |
| D12 · 05/09 | M7 Đo lại & tối ưu | T-012 |
| D13 · 06/09 | M7 Đóng gói demo (**đệm dự phòng**) | T-013 |

> ⚠️ **Quy tắc chống trượt tiến độ**: nếu một mốc trễ quá nửa ngày, **cắt scope P1/P2 của mốc đó**
> chứ không lấn sang ngày của mốc sau. Hạng mục được phép cắt: F13 dashboard thống kê, F14 cảnh báo
> hạn mức, F16 CSAT. Hạng mục **không được cắt**: T-008 (eval), T-010 (PII), T-011 (HITL), ADR-005
> (idempotency) — đó là các điểm chấm cốt lõi, xem `docs/PRD.md` mục 6.

---

## ⏳ Đang Dở
> Agent mới vào phiên: đọc mục này trước tiên.

- *(Trống — không có task nào đang cầm dở.)*
- **Việc kế tiếp phải cầm**: **T-008 — Eval harness** (D3 · 27/08). Đây là task **không được cắt**.
  Đọc trước: `docs/intent-taxonomy.md` (10 nhãn + 9 dạng đầu vào tiếng Việt phải phủ),
  `docs/DATA-MODEL.md` mục 6 (11 case khó đã cài sẵn, dùng làm câu hỏi cho golden set),
  và ADR-008 (model đã ghim — **không** dùng alias `-latest`, sẽ phá tính tái lập của eval).

---

## ☐ Hàng Đợi (Backlog)

| ID | Task | Ngày | Ưu tiên | Nghiệm thu (1 dòng) | Ghi chú |
|---|---|---|---|---|---|
| T-008 | **Eval harness** | D3 | P0 | `.venv/Scripts/python.exe -m eval.run_eval` in bảng: intent accuracy · recall@3 · p95 TTFT · token/lượt · số ca lộ PII | 80 câu intent + 30 câu RAG + 20 prompt red-team. **Không được cắt** |
| T-009 | Vertical slice + **deploy sớm** | D4–D5 | P0 | Login JWT → WS stream → `fare.inquiry` qua RAG → ghi log, chạy được **trên Vercel + Render**, không phải localhost | Deploy là rủi ro lớn nhất → phải nổ ở D5, không để cuối sprint |
| T-004 | LangGraph state & router | D6–D8 | P0 | Router 1 lần gọi LLM ra `{intent, confidence, slots}`; rẽ nhánh đúng 10 nhãn; slot-filling hỏi lại khi thiếu | Đo lại bằng T-008 sau khi xong |
| T-010 | Guardrail PII + fallback | D6–D8 | P0 | PII token hoá **trước khi** vào context; red-team 20 prompt → 0 ca lộ; tắt DB/LLM → agent xin lỗi, không văng stacktrace | ADR-004, ADR-001. **Không được cắt** |
| T-011 | **HITL duyệt hoàn tiền** | D7–D8 | P0 | Hoàn > ngưỡng → `interrupt()`; CSKH duyệt → graph resume → khách nhận thông báo trên đúng phiên cũ | ADR-003. **Không được cắt** |
| T-005 | Backend API cho dashboard | D9 | P0 | Endpoint hàng đợi HITL, transcript + tool trace, duyệt/từ chối (từ chối bắt buộc có lý do), thống kê | Phân quyền: `customer` gọi → 403 |
| T-006 | Frontend Next.js | D9–D11 | P0 | Chat khách (stream, trạng thái chờ duyệt) + Dashboard CSKH (hàng đợi, tool trace, nút duyệt) | Kiểm ở 375px / 768px / 1280px |
| T-012 | Đo lại, tối ưu, chaos test | D12 | P0 | Chạy T-008 lần cuối đạt cả 3 ngưỡng; test tắt LLM/DB/tool xem fallback | Nếu intent < 90% → chữa theo thứ tự ở `intent-taxonomy.md` mục 4 |
| T-013 | Đóng gói & demo | D13 | P1 | README có sơ đồ kiến trúc, video demo, kịch bản 5 phút chạy trọn luồng HITL | Ngày này cũng là đệm dự phòng |
| T-014 | Dashboard thống kê & cảnh báo hạn mức | D10–D11 | P1 | 4 chỉ số + 2 biểu đồ khớp DB; bơm dữ liệu vượt ngưỡng → hiện cảnh báo | F13, F14 — **được phép cắt nếu trễ tiến độ** |
| T-015 | Thu thập CSAT | D11 | P2 | Cuối phiên hỏi mức 1–5, ghi vào bảng `csat` | F16 — cắt đầu tiên nếu thiếu thời gian |

---

## ✅ Đã Xong

| ID | Task | Ngày xong | Ghi chú / Link JOURNAL |
|---|---|---|---|
| T-001 | Xây dựng bộ tài liệu tri thức RAG (7 file) | 2026-08-25 | JOURNAL `[2026-08-25]` — 7 file trong `data/knowledge_base/`, số liệu đối soát từ nguồn công bố |
| T-007 | D1: Đóng băng đặc tả, intent taxonomy & 7 ADR | 2026-08-25 | JOURNAL `[2026-08-25]` — PRD, intent-taxonomy, ADR-001…007, architecture, glossary, codemap, DoD |
| T-002 | Schema PostgreSQL + seed data | 2026-08-26 | JOURNAL `[2026-08-26]` — **14 bảng** (nhiều hơn 12 dự kiến) đã áp lên Neon; 311 chuyến + 11 case khó; 4 truy vấn kiểm chứng đã chạy thật |
| T-003 | Tool contracts (Pydantic) | 2026-08-26 | JOURNAL `[2026-08-26]` — 8 tool, 5 ghi / 3 đọc, error taxonomy 3 nhánh, 11 test pass, ruff sạch |

---

## ❄️ Tạm Hoãn

| ID | Task | Lý do hoãn | Điều kiện để mở lại |
|---|---|---|---|
| — | — | — | — |

---

## 🚫 Cố Ý Không Làm Trong Sprint Này

Ghi ở đây để agent phiên sau không tự mở việc mới (chi tiết ở `docs/PRD.md` mục 5):
đăng ký/quên mật khẩu/OTP · thanh toán thật · bản đồ thật · ứng dụng di động · đa ngôn ngữ ·
fine-tune model · CI/CD tự động · load test quy mô lớn.
