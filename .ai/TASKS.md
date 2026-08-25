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

## ⏳ Đang Dở
> Agent mới vào phiên: đọc mục này trước tiên.

- **T-001** — Xây dựng Bộ tài liệu tri thức RAG (Knowledge Base) · `P0` · _Người cầm: Antigravity_
  - **Bối cảnh**: Cung cấp tri thức nền tảng chuẩn mực về biểu phí, hủy chuyến, hoàn tiền, thất lạc đồ, tiêu chuẩn tài xế Xanh SM cho Agent tra cứu RAG.
  - **Nghiệm thu**: Đầy đủ 7 file markdown trong `data/knowledge_base/` với cấu trúc chuẩn.
  - **Đã làm tới đâu**: Đã hoàn thành toàn bộ 7 file markdown chi tiết theo nghiệp vụ xe điện Xanh SM.
  - **Bước tiếp theo**: Thiết kế Database Schema (PostgreSQL) và Pydantic Tool Contracts.
  - **Vướng mắc**: Không

---

## ☐ Hàng Đợi (Backlog)

| ID | Task | Ưu tiên | Nghiệm thu (1 dòng) | Ghi chú |
|---|---|---|---|---|
| T-002 | Thiết kế Database Schema & Seed Data | P0 | Có file SQL DDL / ORM models cho users, rides, tickets, refunds | |
| T-003 | Thiết kế Tool Contracts & Pydantic Schemas | P0 | Có đầy đủ Pydantic models cho book, cancel, refund, ticket tools | |
| T-004 | Xây dựng LangGraph State & Router Nodes | P0 | Graph chạy phân loại intent và rẽ nhánh chính xác | |
| T-005 | Xây dựng Backend FastAPI & WebSocket Streaming | P0 | API chat streaming, JWT auth, HITL webhook | |
| T-006 | Xây dựng Frontend Next.js + HITL Dashboard | P1 | UI Chat Khách + Dashboard CSKH duyệt hoàn tiền | |

---

## ✅ Đã Xong

| ID | Task | Ngày xong | Ghi chú / Link JOURNAL |
|---|---|---|---|
| — | — | — | — |

---

## ❄️ Tạm Hoãn

| ID | Task | Lý do hoãn | Điều kiện để mở lại |
|---|---|---|---|
| — | — | — | — |
