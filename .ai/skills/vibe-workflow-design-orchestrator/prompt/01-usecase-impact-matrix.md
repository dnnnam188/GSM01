# Prompt BT1 — Usecase design: Ma trận Hiệu quả × Độ phức tạp

> Mục đích: Phân tích list vấn đề DN, chấm 2 trục, suggest thứ tự automate.
> Dán vào: Claude Pro / Claude.ai web / Gemini.

```text
BỐI CẢNH:
Tôi là quản lý phòng ban tại một doanh nghiệp. Công ty đang apex AI Automation nhưng chưa biết nên bắt đầu từ quy trình nào. Dưới đây là danh sách các vấn đề/quy trình lặp lại đang tồn tại (ghi bằng ngôn ngữ tự nhiên):

[LIST VẤN ĐỀ — dán list 8-10 vấn đề ở đây, ví dụ:
- Nhân viên sales tổng hợp báo cáo doanh số từ 3 cửa hàng mỗi cuối tuần (mất 4 giờ)
- Phòng CSKH trả lời cùng 5 câu hỏi lặp đi lặp lại qua Zalo
- HR sàng lọc 200 CV mỗi đợt tuyển bằng tay
- Kế toán nhập tay hóa đơn vào Excel
- Marketing viết caption FB mỗi ngày
- ...]

CHỈ DẪN:
1. Với từng vấn đề, chấm 2 trục:
   - HIỆU QUẢ (Impact 1-5): tác động đến chi phí/thời gian/chất lượng nếu giải quyết (5 = rất lớn). Ví dụ: tiết kiệm ≥10 giờ/tuần hoặc giảm ≥50% lỗi = Impact 5; tiết kiệm ~1 giờ = Impact 2.
   - ĐỘ PHỨC TẠP (Difficulty 1-5): nỗ lực triển khai AI Automation (data sẵn, quy tắc rõ, ít ngoại lệ = dễ = 1; phi cấu trúc, nhiều role, dữ liệu rác = khó = 5). Ví dụ: cần OCR PDF scan = Difficulty 4; đổi tên file text = Difficulty 1.
2. Xếp từng use-case vào 1 trong 4 góc ma trận:
   - LÀM NGAY (quick win): Hiệu quả ≥4 AND Phức tạp ≤2
   - LÊN KẾ HOẠCH: Hiệu quả ≥4 AND Phức tạp ≥3
   - KHI RẢNH: Hiệu quả ≤3 AND Phức tạp ≤2
   - BỎ: Hiệu quả ≤3 AND Phức tạp ≥3
3. Suggest thứ tự automate: xếp LÀM NGAY trước, rồi LÊN KẾ HOẠCH.

TIÊU CHUẨN ĐẦU RA:
- 1 bảng: | # | Use-case | Impact (1-5) | Difficulty (1-5) | Góc ma trận | Lý do ngắn |
- 1 ma trận text 2×2 hiển thị 4 góc (có thể dùng Markdown table hoặc ASCII).
- Top-3 use-case nên automate TRƯỚC, kèm 1 câu lý do mỗi use-case.
- Giọng tiếng Việt rõ ràng, không phóng đại số liệu nếu không có cơ sở.
```
