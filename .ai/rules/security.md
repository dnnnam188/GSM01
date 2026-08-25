# Security & Secrets Management

## 1. Quản Lý Biến Môi Trường (.env)
- **Tuyệt đối không commit tệp chứa secret**: Tệp `.env`, `.env.local`, `.env.production` phải luôn nằm trong `.gitignore`.
- Sử dụng `.env.example` để mô tả danh sách các biến môi trường cần thiết kèm giá trị mẫu không chứa thông tin nhạy cảm.

## 2. API Keys & Thông Tin Nhạy Cảm
- Không hardcode API key, mật khẩu, access token trực tiếp vào mã nguồn.
- Kiểm tra kỹ trước khi commit: Đảm bảo không để lộ thông tin credentials trong code, test cases hoặc tài liệu.

## 3. Thực Thi Lệnh An Toàn
- Không chạy các lệnh xóa nguy hiểm (như `Remove-Item -Recurse -Force` trên thư mục root hoặc system).
- Luôn kiểm tra kỹ thư mục làm việc hiện tại trước khi thực hiện các tác vụ ghi đè / xóa file hàng loạt.
