# Testing & Bug Fixing Methodology

## 1. Quy Trình Sửa Bug Chuẩn (4 Bước)
Khi được yêu cầu sửa lỗi (fix bug), AI Agent phải tuân thủ nghiêm ngặt quy trình:
1. **Tái lập lỗi (Reproduce)**: Xác định điều kiện gây lỗi theo đúng hành vi/trải nghiệm của người dùng hoặc viết test case tái lập lỗi trước.
2. **Khoanh vùng nguyên nhân (Root Cause)**: Tìm chính xác đoạn code/logic gây ra lỗi, không đoán mò hay sửa chữa lan man.
3. **Thực hiện sửa đổi (Fix)**: Sửa đúng trọng tâm, giữ nguyên logic xung quanh và đảm bảo không phá vỡ tính năng hiện có (no regression).
4. **Xác minh thực tế (Verify)**: Chạy lại test suite, linting, kiểm tra hành vi thực tế trước khi kết luận đã hoàn thành.

## 2. Tiêu Chuẩn Kiểm Thử (Testing Standards)
- **Unit Tests**: Kiểm tra các hàm logic độc lập, xử lý các trường hợp biên (edge cases, null, undefined, invalid input).
- **Integration Tests**: Kiểm tra sự phối hợp giữa các module/service/API.
- **Tự động hóa**: Đảm bảo tất cả test pass 100% trước khi bàn giao task.
