# Prompt BT4 — Vẽ Mermaid: activity / sequence diagram

> Mục đích: Sinh mã Mermaid (activity hoặc sequence) cho workflow to-be có hardening.
> Dán vào: Claude Pro / Antigravity (Workflow system). Render tại mermaid.live.

```text
BỐI CẢN:
Tôi cần vẽ sơ đồ workflow mới (to-be + hardening) cho quy trình "[TÊN USE-CASE]". Dưới đây là workflow đã thiết kế:

[DÁN BẢNG TO-BE + HARDENING TỪ BT2, BT3]

Kiểu diagram ưu tiên: [ACTIVITY (luồng công việc) / SEQUENCE (tương tác giữa các role/hệ thống)].

CHỈ DẪN:
Viết mã Mermaid mô tả trực quan workflow to-be có hardening:
- Mỗi bước là 1 node, ghi rõ ai làm + công cụ/hệ thống.
- Node AI (bước Automate) tô màu nền nổi bật: class aiNode fill:#FFE0B2,stroke:#FB8C00,stroke-width:2px.
- Node Human-in-the-loop (HITL) tô màu cảnh báo: class hitlNode fill:#FFCDD2,stroke:#E53935,stroke-width:2px.
- Node fallback (nhánh xử lý lỗi) tô màu xám: class fallbackNode fill:#ECEFF1,stroke:#607D8B,stroke-width:2px.
- Bước rẽ nhánh điều kiện dùng node hình thoi {} (ví dụ: {Input đạt chất lượng?}).
- Nếu activity: dùng flowchart LR (trái qua phải). Nếu sequence: dùng sequenceDiagram (tương tác dọc giữa các actor).

TIÊU CHUẨN ĐẦU RA:
- CHỈ trả về 1 khối mã Mermaid hợp lệ trong ```mermaid ... ```.
- KHÔNG kèm lời giải thích dài.
- Tối đa 8 node (giữ sơ đồ tinh gọn).
- BẮT BUỘC ≥1 node HITL.
- Tất cả label tiếng Việt, chính tả chuẩn.
```
