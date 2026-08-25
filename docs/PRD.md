# Product Requirements Document (PRD)

> 📝 *Mẫu tài liệu đặc tả yêu cầu sản phẩm. Bạn hãy bổ sung nội dung chi tiết khi xác định cụ thể đề tài.*

## 1. Tóm Tắt Sản Phẩm (Executive Summary)
- **Tên sản phẩm**: [Tên dự án]
- **Vấn đề cần giải quyết (Problem Statement)**: [Mô tả nỗi đau / vấn đề của người dùng]
- **Giải pháp đề xuất (Proposed Solution)**: [Mô tả giải pháp sản phẩm mang lại]

## 2. Chân Dung Người Dùng (User Personas)
- **Nhóm 1**: [Mô tả đối tượng người dùng chính, hành vi và mục tiêu]
- **Nhóm 2**: [Mô tả đối tượng người dùng phụ hoặc quản trị viên]

## 3. Danh Sách Yêu Cầu Tính Năng (Feature Requirements)
| ID | Tên tính năng | Mức độ ưu tiên | Mô tả chi tiết | Tiêu chí nghiệm thu (Acceptance Criteria) |
|---|---|---|---|---|
| F01 | Xác thực người dùng | P0 (Bắt buộc) | Đăng nhập, đăng ký, quên mật khẩu | Đăng nhập thành công trả về JWT token |
| F02 | Dashboard chính | P0 (Bắt buộc) | Hiển thị tổng quan các dữ liệu chính | Load trong vòng dưới 1.5s, có skeleton |
| F03 | Quản lý dữ liệu | P1 (Quan trọng) | CRUD các thực thể chính | Form có validation đầy đủ |
| F04 | Xuất báo cáo | P2 (Mở rộng) | Xuất file PDF / Excel | Tải về file đúng định dạng |

## 4. Yêu Cầu Phi Chức Năng (Non-Functional Requirements)
- **Hiệu năng**: Thời gian phản hồi API < 200ms, tải trang đầu < 2s.
- **Bảo mật**: HTTPS, mã hóa mật khẩu bằng bcrypt/argon2, chống SQL Injection/XSS.
- **Khả năng mở rộng**: Thiết kế module hóa, dễ dàng tích hợp thêm dịch vụ mới.
