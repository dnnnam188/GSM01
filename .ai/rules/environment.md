# Environment & Execution Guidelines (Windows OS)

## 1. Môi Trường Hệ Điều Hành
- Hệ điều hành: **Windows** (Shell mặc định: PowerShell hoặc Command Prompt).
- Đường dẫn file: Khi chạy lệnh shell trên Windows, chú ý dấu phân cách thư mục (`\` hoặc `/`), bọc đường dẫn có khoảng trắng trong dấu ngoặc kép.

## 2. Python Environment
- **Bắt buộc dùng môi trường ảo**: Không bao giờ cài đặt hoặc chạy gói thư viện vào Python Global.
- Sử dụng `uv` hoặc `.venv`:
  - Kích hoạt venv trên Windows PowerShell: `.\.venv\Scripts\Activate.ps1`
  - Hoặc chạy trực tiếp qua `uv`: `uv run python <script.py>` hoặc `uv pip install <package>`

## 3. Node.js & Web Environment
- Sử dụng trình quản lý gói nhất quán (`npm`, `pnpm` hoặc `yarn`).
- Không sửa trực tiếp các tệp trong `node_modules/`, `dist/`, `build/`.
- Khi khởi tạo dev server: Sử dụng port mặc định hoặc thông báo rõ port đang chạy.
