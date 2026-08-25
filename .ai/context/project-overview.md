# Project Overview (Tổng Quan Dự Án)

> Chi tiết tính năng → `docs/PRD.md` · Kiến trúc → `.ai/context/architecture.md`
> · Vì sao chọn cách này → `.ai/context/decisions.md`

## 1. Tên & Mục Tiêu Dự Án

- **Mã dự án**: GSM-01
- **Tên dự án**: AI Agent Trợ lý CSKH đặt xe & xử lý khiếu nại (dịch vụ gọi xe Xanh SM)
- **Mục tiêu chính**: Thay thế phần lớn thao tác tra cứu thủ công của tổng đài bằng một AI Agent biết
  lập kế hoạch nhiều bước — phân loại ý định, truy vấn dữ liệu chuyến đi, tra chính sách bằng RAG,
  gọi tool đặt/huỷ/hoàn tiền/tạo ticket, và **dừng xin phê duyệt của con người** khi vượt ngưỡng rủi ro.
- **Đối tượng người dùng**: hai vai trò — **khách hàng** (`customer`) và **nhân viên CSKH** (`agent`).

## 2. Công Nghệ Sử Dụng (Tech Stack)

- **Frontend**: Next.js (React) + Tailwind CSS — deploy trên Vercel
- **Backend**: Python 3.11+ · FastAPI · WebSocket streaming — deploy trên Render
- **Điều phối agent**: LangGraph (state graph, checkpointer, `interrupt()` cho HITL)
- **Cơ sở dữ liệu**: PostgreSQL + `pgvector` (Neon/Supabase) — **một DB duy nhất**, xem ADR-002
- **LLM**: Gemini Flash làm chính, OpenRouter làm dự phòng — xem ADR-001
- **Xác thực**: JWT, hai vai trò `customer` / `agent`
- **Môi trường**: Windows + `uv` cho Python, `npm` cho Node — xem `.ai/rules/environment.md`

## 3. Các Tính Năng Chính

Danh sách đầy đủ và tiêu chí nghiệm thu nằm ở `docs/PRD.md` (F01–F16). Tóm tắt:

- [ ] **Chat streaming 2 vai trò**: đăng nhập JWT, WebSocket, token hiện dần (F01–F02)
- [ ] **Agent đa bước**: phân loại 10 intent, RAG chính sách, gọi tool nghiệp vụ (F03–F08)
- [ ] **Memory & truy vết**: bộ nhớ hội thoại 3 tầng, log mọi tool call vào DB (F09–F10)
- [ ] **HITL duyệt hoàn tiền**: graph dừng, CSKH duyệt, hội thoại tự chạy tiếp (F11–F12)
- [ ] **Dashboard & cảnh báo**: thống kê ticket/CSAT/chi phí token, cảnh báo vượt hạn mức (F13–F14)
- [ ] **Guardrail**: PII token hoá trước khi vào LLM, fallback khi tool lỗi (F15)

## 4. Ràng Buộc Cứng (ba con số quyết định điểm số)

| Chỉ số | Ngưỡng | Đo bằng |
|---|---|---|
| Độ chính xác intent | ≥ 90% | `eval/run_eval.py` trên golden set có nhãn |
| Độ trễ phản hồi | < 3s (p95 TTFT) | Đo trên WebSocket, 50 lượt |
| Rò rỉ PII | = 0 | Bộ red-team 20 prompt |

> Ba con số này phải **đo được từ ngày thứ ba của sprint**, không để tới cuối. Đó là lý do bộ eval
> được xây **trước** khi xây agent.

## 5. Các Mốc Phát Triển (sprint 13 ngày: 2026-08-25 → 2026-09-06)

| Mốc | Ngày | Nội dung |
|---|---|---|
| **M1 — Đặc tả đóng băng** | D1 | PRD, intent taxonomy, 7 ADR, tài liệu context |
| **M2 — Hợp đồng dữ liệu** | D2 | Schema 12 bảng, seed có case khó, Pydantic tool contract |
| **M3 — Bộ eval chạy được** | D3 | `eval/run_eval.py` ra bảng số |
| **M4 — Vertical slice online** | D4–D5 | Một luồng chạy xuyên, **đã deploy** |
| **M5 — Agent đầy đủ** | D6–D8 | LangGraph, 4 tool, HITL, memory, guardrail |
| **M6 — Giao diện** | D9–D11 | Chat khách + dashboard CSKH |
| **M7 — Nghiệm thu & demo** | D12–D13 | Đo lại eval, chaos test, video demo |

Trạng thái từng task → `.ai/TASKS.md`.
