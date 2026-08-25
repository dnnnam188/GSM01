# Bug History & Troubleshooting Log

> 💡 *Mục đích: Ghi lại các lỗi oái oăm hoặc các vấn đề kỹ thuật đặc thù đã giải quyết thành công để các AI Agent không bao giờ lặp lại lỗi tương tự.*

## Mẫu Ghi Lỗi (Template)

### [YYYY-MM-DD] - Tên lỗi ngắn gọn
- **Hiện tượng**: Mô tả lỗi xảy ra như thế nào, mã lỗi (nếu có).
- **Nguyên nhân cốt lõi**: Giải thích lý do gây ra lỗi.
- **Giải pháp xử lý**: Cách đã sửa và tệp đã thay đổi.
- **Lưu ý phòng ngừa**: Điều cần tránh trong tương lai.

---

## Danh Sách Lỗi Đã Xử Lý

### [Ví Dụ] [2026-08-24] - Lỗi đường dẫn Windows khi chạy script PowerShell
- **Hiện tượng**: Lệnh shell báo lỗi không tìm thấy đường dẫn có chứa dấu cách `Side Project`.
- **Nguyên nhân**: Quên bọc đường dẫn trong dấu ngoặc kép khi truyền tham số trên PowerShell.
- **Giải pháp**: Luôn sử dụng `"$Path"` hoặc dấu nháy kép `"` cho mọi đường dẫn tệp.
- **Lưu ý phòng ngừa**: Luôn kiểm tra tính tương thích của shell Windows trong `.ai/rules/environment.md`.
