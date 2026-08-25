# Sample — Workflow Design Doc đầy đủ (tổ chức tài liệu)

> Output hoàn chỉnh sau BT2-BT3. Input cho BT4-BT6.

## 1. Hiện trạng (as-is)
Xem `sample-as-is.md` — 6 bước thủ công, 5 giờ/tuần lãng phí.

## 2. To-be ESIA
Xem `sample-esia-tobe.md` — 7 bước, AI Agent + HITL review plan.

## 3. Hardening cho production

| Bước to-be | Fallback branch | Execution log | Edge case | HITL |
|------------|-----------------|---------------|-----------|------|
| 2 Phân loại | File không đọc được (ảnh mờ, PDF scan) → flag "cần kiểm tra tay" | log: file, lý do fail | File 0 byte, file mã hóa | — |
| 4 Build plan | Plan quá lớn (>500 file) → chia batch 100 file | log: số file, vị trí đích | Trùng tên sau chuẩn hóa → thêm suffix -1 -2 | **User review plan** |
| 6 Copy file | Copy fail (ổ cứng đầy, quyền) → giữ gốc, cảnh báo | log: file, trạng thái OK/FAIL | File đang mở → bỏ qua, log | Giữ bản gốc tới khi user xác nhận |

**Compliance note:** File hợp đồng/PII chỉ giữ local hoặc Drive nội bộ phân quyền — KHÔNG đẩy Drive công khai.

**Mức độ tin cậy:** sau hardening đạt 6/6 thuộc tính:
- ✅ fault-tolerant (fallback mỗi bước)
- ✅ observable (execution log đầy đủ)
- ✅ workable (script Python đơn giản)
- ✅ auditable (log + report CSV)
- ⚠️ scalable (cần batch cho >500 file)
- ⚠️ idempotent (chạy lại tạo bản copy trùng — cần check hash trước)

## 4. Mermaid
Xem `sample-mermaid.mmd`.

## 7. Danh sách bước cần tự động

| Bước A | Công cụ | HITL | Fallback khi AI lỗi |
|--------|---------|------|---------------------|
| Phân loại file | AI Agent (Claude Code) | — | Flag kiểm tra tay |
| Build plan | AI Agent | **User review** | Chia batch nhỏ |
| Copy file | Script Python | Giữ gốc | Cảnh báo + giữ gốc |
| Ghi log | Script Python | — | Ghi log riêng |
