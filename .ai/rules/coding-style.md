# Coding Style & Architecture Guidelines

## 1. Nguyên Tắc Cốt Lõi
- **Đơn giản & Rõ ràng (KISS & Clean Code)**: Ưu tiên code dễ đọc, dễ bảo trì hơn code quá ngắn gọn nhưng khó hiểu.
- **Tách biệt Trách nhiệm (Single Responsibility)**: Mỗi hàm/module chỉ thực hiện một nhiệm vụ cụ thể.
- **Tự giải thích (Self-documenting)**: Đặt tên biến, hàm có ý nghĩa rõ ràng, hạn chế comment thừa thãi không cần thiết.

## 2. Quy Chuẩn Đặt Tên (Naming Conventions)
- **Biến & Hàm**: `camelCase` (ví dụ: `getUserProfile`, `totalAmount`).
- **Lớp & Interface**: `PascalCase` (ví dụ: `UserProfile`, `PaymentGateway`).
- **Hằng số**: `UPPER_SNAKE_CASE` (ví dụ: `MAX_RETRY_COUNT`, `DEFAULT_TIMEOUT`).
- **Tệp & Thư mục**: `kebab-case` (ví dụ: `user-service.ts`, `auth-controller.js`).

## 3. Quản Lý Lỗi (Error Handling)
- Luôn bọc các tác vụ bất đồng bộ (I/O, API, Database) trong khối `try/catch` có xử lý lỗi cụ thể.
- Trả về thông báo lỗi thân thiện với người dùng, log chi tiết lỗi kỹ thuật ở phía máy chủ.
- Không nuốt lỗi (silent fail) hoặc để catch rỗng.
