# Sample — To-be ESIA (workflow tổ chức tài liệu)

> Use-case: tổ chức tài liệu. Output BT2 → input BT3.

## To-be (sau ESIA)

| # | Bước (to-be) | E/S/I/A | Chi tiết tối ưu & HITL | Ai làm | Nhánh automation |
|---|--------------|---------|------------------------|--------|------------------|
| 1 | Quét folder, đọc metadata file | I | Gom tất cả file về 1 list + metadata (tên, loại, ngày, size) | AI | AI Agent |
| 2 | Phân tích nội dung → phân loại (project/knowledge/reference/SOP...) | A | AI đọc nội dung (text) hoặc metadata (ảnh/PDF) → gán loại | AI | AI Agent |
| 3 | Chuẩn hóa tên: `[name] - [type] - [version] - [date].[ext]` | S | AI đề xuất tên mới theo policy | AI | AI Agent |
| 4 | Tham chiếu policy (cấu trúc folder + cách lưu) → build plan di chuyển | A | AI map từng file → vị trí đích. **HITL: USER REVIEW PLAN trước khi thực thi** | AI + User | AI Agent |
| 5 | Phát hiện file trùng (hash) → đánh dấu gộp | A | AI so hash, đề xuất giữ bản mới nhất | AI | Script Python |
| 6 | Thực thi: copy file đúng vị trí (KHÔNG xóa gốc) | A | AI Agent chạy script copy. **HITL: giữ bản gốc tới khi user xác nhận** | AI Agent | Script Python |
| 7 | Sinh báo cáo: file nào → đâu, file trùng, file nghi ngờ | A | Log vào `organize-report.csv` | AI | Script Python |

**Bước cần HITL (bắt buộc):**
- **Bước 4 (review plan):** user duyệt plan trước khi AI move — tránh file bị đặt sai chỗ.
- **Bước 6 (giữ bản gốc):** KHÔNG xóa file gốc tự động — copy trước, user xác nhận xong mới xóa tay.

**Compliance note:** File chứa thông tin nhạy cảm (hợp đồng, PII) → KHÔNG đẩy lên Google Drive công khai, chỉ giữ local hoặc Drive nội bộ có phân quyền.
