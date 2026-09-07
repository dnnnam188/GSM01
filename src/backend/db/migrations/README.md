# Database migrations

`001_initial_schema` hiện dùng `../schema.sql` để bootstrap database cũ và được
ghi vào bảng `schema_migrations`. Từ migration tiếp theo:

1. Tạo file SQL tăng dần, ví dụ `002_add_x.sql`.
2. Thêm file đó vào runner theo thứ tự.
3. Không sửa migration đã được production ghi nhận.
4. Chạy migration trên staging, backup rồi mới chạy production.

`seed.py` và `scripts.demo_reset` chỉ dành cho môi trường staging/demo; chúng
không được phép chạy khi `ENVIRONMENT=production`.
