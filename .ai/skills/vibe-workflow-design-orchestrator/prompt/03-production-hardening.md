# Prompt BT3 — Improve workflow cho production: Hardening

> Mục đích: Bổ sung 4 lớp hardening (fallback/log/edge/HITL) vào workflow to-be.
> Dán vào: Claude Pro / Antigravity (Knowledge system).

```text
BỐI CẢNH:
Tôi vừa thiết kế workflow mới (to-be) cho quy trình "[TÊN USE-CASE]". Dưới đây là bảng to-be:

[DÁN BẢNG TO-BE TỪ BT2 — gồm cột Bước / E-S-I-A / Chi tiết / AI-Người / Nhánh automation]

Workflow này hiện mới chỉ là happy case — chạy demo được nhưng chưa đủ tin cậy để chạy production.

CHỈ DẪN:
Bổ sung 4 lớp hardening vào workflow to-be để chạy production được:

1. FALLBACK BRANCH: với mỗi bước Automate, định nghĩa nhánh xử lý khi input kém chất lượng hoặc AI lỗi (vd: AI không đọc được hóa đơn mờ → chuyển người xem, hoặc cảnh báo Slack).
2. EXECUTION LOG: định nghĩa cần log gì ở mỗi bước (thời gian, input hash, trạng thái OK/WARN/FAIL, output). Log KHÔNG lưu PII gốc chưa ẩn danh — chỉ ghi metadata + hash.
3. EDGE CASE: liệt kê 3-5 trường hợp đặc biệt (input rỗng, format sai, ngoài giờ làm, khối lượng đột biến) và cách xử lý.
4. HUMAN-IN-THE-LOOP: xác nhận lại các bước cần con người review trước khi đi tiếp — rõ ai duyệt, duyệt ở đâu, trong bao lâu.

TIÊU CHUẨN ĐẦU RA:
- 1 bảng hardening: | Bước to-be | Fallback | Log | Edge case | HITL (ai/khi nào) |
- 1 đoạn "Compliance note" ngắn: bước nào liên quan dữ liệu cá nhân / tiền bạc → bắt buộc HITL theo quy định nội bộ.
- 1 đoạn "Mức độ tin cậy": workflow này sau hardening đạt được bao nhiêu/6 thuộc tính (fault-tolerant, observable, scalable, workable, idempotent, auditable) — đánh giá thẳng thắn.
- Tiếng Việt, thực tế, không overclaim.
```
