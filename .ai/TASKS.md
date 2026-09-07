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

*Trống.*

---

## ☐ Hàng Đợi (Backlog)

*Trống — toàn bộ 15 task đã xong. T-006 vẫn ở ⏳ vì chưa kiểm giao diện bằng mắt
(người dùng đã quyết định chấp nhận). Việc còn lại nằm ngoài code: gộp nhánh vào
`main`, nhập key vào Render, quay video demo.*

---

## ✅ Đã Xong

| ID | Task | Ngày xong | Ghi chú / Link JOURNAL |
|---|---|---|---|
| T-016 | Chốt quota Gemini và tạm tắt provider fallback | 2026-09-07 | JOURNAL `[2026-09-07]` — Flash Lite router/answer, `GEMINI_RPM=15`, fallback gated bằng `FALLBACK_ENABLED=false`; test 92 pass / 1 skip |
| T-006 | Frontend Next.js (chat khách + dashboard CSKH) | 2026-08-27 | **Người dùng tự xem và nghiệm thu**, không phải qua kiểm trực quan của agent — "frontend cơ bản vậy là được, đơn giản dễ hiểu". `npm run build` sạch, đã chạy thật trên Vercel |
| T-015 | Thu thập CSAT cuối phiên (F16) | 2026-08-27 | JOURNAL `[2026-08-27] D12` — hỏi 1–5 sau 2 lượt trả lời; 13 test, trọng tâm là **không chấm được lên phiên của người khác**; chạy thật qua WebSocket → dashboard nhích 4,25 → 4,4 |
| T-014 | Dashboard thống kê (F13) & cảnh báo hạn mức (F14) | 2026-08-26 | JOURNAL `[2026-08-26] D11` — 4 chỉ số + 2 biểu đồ, **10 test đối soát lại từng số bằng truy vấn độc lập**; bơm vượt ngưỡng qua HTTP: OK→DANGER→OK; mốc ngày sửa về giờ VN |
| T-001 | Xây dựng bộ tài liệu tri thức RAG (7 file) | 2026-08-25 | JOURNAL `[2026-08-25]` — 7 file trong `data/knowledge_base/`, số liệu đối soát từ nguồn công bố |
| T-007 | D1: Đóng băng đặc tả, intent taxonomy & 7 ADR | 2026-08-25 | JOURNAL `[2026-08-25]` — PRD, intent-taxonomy, ADR-001…007, architecture, glossary, codemap, DoD |
| T-002 | Schema PostgreSQL + seed data | 2026-08-26 | JOURNAL `[2026-08-26]` — **14 bảng** (nhiều hơn 12 dự kiến) đã áp lên Neon; 311 chuyến + 11 case khó; 4 truy vấn kiểm chứng đã chạy thật |
| T-003 | Tool contracts (Pydantic) | 2026-08-26 | JOURNAL `[2026-08-26]` — 8 tool, 5 ghi / 3 đọc, error taxonomy 3 nhánh, 11 test pass, ruff sạch |
| T-013 | Đóng gói: README + sơ đồ kiến trúc, kịch bản demo 5 phút, script reset dữ liệu | 2026-08-26 | JOURNAL `[2026-08-26] D10` — README thật, `docs/DEMO.md`, `scripts/demo_reset.py`; **video chưa quay** (cần người thực hiện) |
| T-012 | Đo lại, chaos test, eval đa lượt + trung thực với nguồn | 2026-08-26 | JOURNAL `[2026-08-26] D9` — intent 97,5% · TTFT p95 1471ms · recall@3 100% · PII 0/20 · đa lượt **8/8** · trung thực **100%** · 69 test pass |
| T-011 | HITL duyệt hoàn tiền bằng `interrupt()` + checkpointer Postgres | 2026-08-26 | JOURNAL `[2026-08-26] D8` — **26/26** kịch bản; graph dừng thật, resume đúng chỗ, khách nhận tin trên phiên đang mở |
| T-005 | Backend API cho dashboard CSKH | 2026-08-26 | JOURNAL `[2026-08-26] D8` — hàng đợi HITL, duyệt/từ chối có ràng buộc lý do, transcript + tool trace, thống kê |
| T-010 | Guardrail PII: token hoá trước khi vào context | 2026-08-26 | JOURNAL `[2026-08-26] D7` — **0/20 ca lộ** (từ 5/20 raw và 2/20 masked); 13 test; `StreamMasker` che ngay trên luồng |
| T-009 | Vertical slice + deploy (JWT 2 vai trò, WebSocket, RAG, ghi vết) | 2026-08-26 | JOURNAL `[2026-08-26] D6e` — **28/28 trên bản deploy thật**, TTFT 945/1135 ms, `gemini-3.5-flash-lite` |
| T-004 | LangGraph + 8 tool nghiệp vụ thật | 2026-08-26 | JOURNAL `[2026-08-26] D6` — graph 5 node, 8 tool, 26/26 kịch bản nghiệp vụ, 50 test pass |
| T-008 | Eval harness (80 intent + 30 RAG + 20 red-team) | 2026-08-26 | JOURNAL `[2026-08-26] D3` — **intent 100% (80/80) · TTFT p95 1926ms · recall@3 100%** · PII baseline 5/20 lộ (mục tiêu T-010) |

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
