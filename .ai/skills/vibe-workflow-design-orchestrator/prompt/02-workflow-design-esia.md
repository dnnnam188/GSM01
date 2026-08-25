# Prompt BT2 — Workflow design: As-is → ESIA to-be

> Mục đích: Mô tả as-is, áp ESIA, đề xuất to-be, phân nhánh automation.
> Dán vào: Antigravity (Planning mode) / Claude Pro (tiếp tục đoạn chat BT1).

```text
BỐI CẢN:
Tôi muốn thiết kế lại quy trình "[TÊN USE-CASE — vd: Tự động tổ chức tài liệu: sắp folder lộn xộn về đúng chuẩn]" — đây là use-case tôi vừa chọn ở bước phân tích ma trận ưu tiên.

CHỈ DẪN:
Bước 1 — Mô tả HIỆN TRẠNG (as-is) thành bảng 5 cột:
| Bước | Người thực hiện | Input | Output | Điểm nghẽn / Lỗi lặp |
Mô tả trung thực, ít nhất 5 bước.

Bước 2 — Áp ESIA vào từng bước as-is, đề xuất QUY TRÌNH MỚI (to-be):
- E (Eliminate): bỏ hẳn bước thừa.
- S (Simplify): đơn giản hóa (giảm thao tác, đồng nhất format, gộp trường).
- I (Integrate): gộp nhiều nguồn về 1 chỗ.
- A (Automate): giao AI tự chạy.
Bảng to-be:
| Bước (to-be) | Hành động E/S/I/A | Chi tiết tối ưu | Ai làm (AI/Người) |

Bước 3 — Với mỗi bước đánh A (Automate), gợi ý 1 trong 3 nhánh automation:
- n8n (workflow automation): bước có quy tắc rõ, kết nối hệ thống (email/Sheet/API).
- AI Agent (Claude Code/Codex/Antigravity/OpenClaw/Hermes): bước cần suy luận, đọc tài liệu, quyết định phi cấu trúc.
- App vibe coding: bước cần giao diện nội bộ cho đội.

QUY TẮC VÀNG: Đừng đánh "Automate" cho mọi bước. Bước sai hậu quả nặng (tiền bạc, dữ liệu cá nhân, quyết định ảnh hưởng người dùng) → KHÔNG tự động hoàn toàn, phải có điểm Human-in-the-loop (HITL).

TIÊU CHUẨN ĐẦU RA:
- 1 bảng as-is (≥5 bước, đủ 5 cột).
- 1 bảng to-be (mỗi bước 1 ký hiệu E/S/I/A + cột AI/Người + cột nhánh automation).
- 1 đoạn ghi rõ: bước nào cần HITL và tại sao.
- Tiếng Việt, không bịa số liệu nếu chưa đo.
```
