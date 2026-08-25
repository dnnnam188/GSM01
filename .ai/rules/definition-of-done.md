# Definition of Done (Tiêu Chuẩn Hoàn Thành)

> ⚠️ **Quy tắc tối thượng**: AI Agent **KHÔNG được tuyên bố "đã xong"** nếu chưa đi hết checklist dưới đây.
> Nếu một mục không thể kiểm chứng được, phải **nói thẳng là chưa kiểm chứng** — tuyệt đối không suy đoán,
> không viết "có thể hoạt động tốt", không bịa kết quả test.

## 1. Checklist Chung (áp dụng mọi task)

- [ ] **Chạy thật, không chỉ "biên dịch được"**: đã thực sự khởi động ứng dụng / mở trang / gọi hàm và quan sát kết quả bằng mắt.
- [ ] **Không có lỗi mới**: console trình duyệt / terminal sạch lỗi và cảnh báo nghiêm trọng.
- [ ] **Không phá tính năng cũ (no regression)**: đã kiểm tra lại các luồng liên quan xung quanh phần vừa sửa.
- [ ] **Đúng phạm vi yêu cầu**: không tự ý thêm tính năng, không tự ý refactor lan man ngoài yêu cầu.
- [ ] **Không để lại rác**: xóa `console.log` debug, code chết, file tạm, dữ liệu giả.
- [ ] **Bảo mật**: không hardcode secret/API key (xem `security.md`).
- [ ] **Đã cập nhật `.ai/TASKS.md`**: chuyển trạng thái task sang ✅.
- [ ] **Đã ghi `.ai/JOURNAL.md`**: một entry theo mẫu `.ai/templates/journal-entry.md`.

## 2. Checklist Bổ Sung Theo Loại Task

### Khi sửa bug
- [ ] Đã tái lập được lỗi **trước khi** sửa (theo 4 bước trong `.ai/skills/testing.md`).
- [ ] Đã xác minh lỗi biến mất **sau khi** sửa, bằng đúng kịch bản đã tái lập.
- [ ] Đã ghi lại vào `.ai/context/bug-history.md` nếu là lỗi khó / dễ tái phạm.

### Khi làm giao diện (UI/UX)
- [ ] Hiển thị đúng ở cả 3 khổ: mobile (~375px), tablet (~768px), desktop (≥1280px).
- [ ] Mọi hành động của người dùng đều có phản hồi trạng thái (loading / success / error).
- [ ] Đạt chuẩn trong `.ai/skills/ui-ux-guide.md`.

### Khi có quyết định kiến trúc
- [ ] Đã ghi một mục ADR vào `.ai/context/decisions.md` (dùng mẫu `.ai/templates/adr.md`).

### Khi thêm/sửa dữ liệu hoặc schema
- [ ] Đã cập nhật tài liệu schema tương ứng trong `docs/`.

## 3. Cách Verify Theo Loại Dự Án

> 📝 *Điền phần này cho đúng dự án hiện tại. Đây là chỗ agent hay bịa nhất — hãy viết lệnh cụ thể.*

| Loại dự án | Lệnh / thao tác verify bắt buộc |
|---|---|
| Web tĩnh (không build) | Mở trang bằng `npx serve .` → kiểm tra thủ công theo checklist mục 2 |
| Node.js / Frontend framework | `npm run lint` → `npm run build` → `npm test` |
| Python | `uv run pytest` → `uv run ruff check` |
| **Dự án này** | *[Điền lệnh thật ở đây]* |

## 4. Khi Không Thể Verify

Nếu môi trường không cho phép kiểm chứng (không có test runner, không mở được trình duyệt, thiếu quyền...):
1. **Nói rõ ràng** mục nào chưa được kiểm chứng và vì sao.
2. Ghi vào JOURNAL ở phần *Vướng mắc*.
3. Để task ở trạng thái ⏳ chứ **không** chuyển ✅.
