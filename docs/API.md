# API & Data Specification

> 📝 *Mẫu tài liệu đặc tả API và lược đồ dữ liệu. Bạn hãy cập nhật các endpoint khi phát triển backend.*

## 1. Quy Chuẩn Chung
- **Base URL**: `https://api.yourdomain.com/v1` (hoặc `http://localhost:8000/api`)
- **Định dạng dữ liệu**: `application/json`
- **Mã phản hồi chuẩn (Status Codes)**:
  - `200 OK`: Thành công.
  - `201 Created`: Tạo mới tài nguyên thành công.
  - `400 Bad Request`: Dữ liệu gửi lên không hợp lệ.
  - `401 Unauthorized`: Chưa đăng nhập hoặc token hết hạn.
  - `403 Forbidden`: Không có quyền truy cập.
  - `404 Not Found`: Không tìm thấy tài nguyên.
  - `500 Internal Server Error`: Lỗi máy chủ.

## 2. Cấu Trúc Phản Hồi Chuẩn (Standard Response Format)

```json
{
  "success": true,
  "data": {},
  "message": "Thao tác thành công",
  "errors": null
}
```

## 3. Danh Sách Endpoints Mẫu

### 3.1. Authentication
- `POST /auth/register` - Đăng ký tài khoản
- `POST /auth/login` - Đăng nhập nhận token
- `POST /auth/refresh` - Làm mới access token

### 3.2. Resources
- `GET /items` - Lấy danh sách (hỗ trợ phân trang `?page=1&limit=20`)
- `POST /items` - Tạo mới
- `GET /items/:id` - Lấy chi tiết
- `PUT /items/:id` - Cập nhật toàn bộ
- `PATCH /items/:id` - Cập nhật một phần
- `DELETE /items/:id` - Xóa
