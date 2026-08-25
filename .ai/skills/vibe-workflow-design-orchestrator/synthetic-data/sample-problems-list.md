# Sample output BT1 — Ma trận use-case (tổ chức tài liệu)

> Dùng nếu HV không chạy xong BT1. Đây là input cho BT2.

## Bảng use-case (folder "Tài liệu" lộn xộn)

| # | Use-case | Impact (1-5) | Difficulty (1-5) | Góc ma trận | Lý do |
|---|----------|--------|------------|-----|-------|
| 1 | Tự động chuẩn hóa tên + phân loại file | 5 | 2 | 🟢 LÀM NGAY | Cứu cả team giờ mỗi tuần, AI làm được ngay |
| 2 | Phát hiện + gộp file trùng | 4 | 2 | 🟢 LÀM NGAY | Script hash đơn giản, lợi ích rõ |
| 3 | Tự động move file đúng folder theo policy | 5 | 3 | 🟡 LÊN KẾ HOẠCH | Cần policy rõ + HITL review plan |
| 4 | Tìm kiếm tài liệu theo ngữ cảnh | 5 | 3 | 🟡 LÊN KẾ HOẠCH | AI rerank mạnh nhưng cần index |
| 5 | Sinh reference_map cho dự án mới | 4 | 3 | 🟡 LÊN KẾ HOẠCH | Tiết kiệm mỗi lần bắt đầu dự án |
| 6 | Nhận diện version mới nhất | 4 | 3 | 🟡 LÊN KẾ HOẠCH | Cần quy tắc version rõ |
| 7 | Xóa file cũ theo retention | 3 | 3 | 🔴 BỎ (tạm) | Rủi ro xóa nhầm cao, để sau |

## Top-3 nên automate TRƯỚC
1. **Chuẩn hóa tên + phân loại file** — quick win rõ, AI Agent làm được ngay,救 cả team.
2. **Phát hiện + gộp file trùng** — script đơn giản, giảm rác folder ngay.
3. **Move file đúng folder theo policy (có HITL)** — cốt lõi, cần policy nhưng lợi ích lớn nhất.

→ Use-case chọn cho BT2: **#3 — Tự động tổ chức tài liệu (move file đúng folder theo policy, có user review).**
