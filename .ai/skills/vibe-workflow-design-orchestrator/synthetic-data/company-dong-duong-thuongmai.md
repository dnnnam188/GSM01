# Synthetic Data — Use-case: Tổ chức & tìm kiếm tài liệu

> ⚠️ DỮ LIỆU GIẢ LẬP CHO TRAINING. Folder/tên file minh hoạ, không phải dữ liệu thật.
> Use-case chính xuyên suốt lab: **tự động tổ chức tài liệu + tìm kiếm tài liệu tham khảo**.

## Bối cảnh
Bạn là quản lý/chiến lược gia trong doanh nghiệp. Hàng ngày bạn nhận hàng chục file từ nhiều nguồn (email, Zalo, Drive, tải về): báo cáo, hợp đồng mẫu, nghiên cứu thị trường, SOP phòng ban, tài liệu đào tạo, ghi chú cuộc họp... Sau 6 tháng, folder "Tài liệu" của bạn thành bãi rác: hàng ngàn file, tên tùy tiện, trùng lặp, không biết bản nào mới, tìm một tài liệu mất nửa tiếng.

## Tình trạng folder hiện tại (minh hoạ — folder lộn xộn)
```
~/Tài liệu/
├── Document(1).pdf
├── Document(2).pdf
├── baocao_final.docx
├── baocao_final_final.docx
├── baocao_final_HOANCHINH.docx
├── IMG_20240315.jpg
├── scan.jpg
├── unknown.png
├── meeting notes.txt
├── New folder/
│   ├── copy of report.xlsx
│   └── untitled.md
├──Hoply mau.docx
├── quy trinh ns v1.docx
├── quy trinh ns v2.docx
├── quytrinhns_final.docx
└── ... (≈ 1.200 file lộn xộn)
```

## 10 vấn đề / quy trình lặp lại (input BT1 — ma trận use-case)

1. **[Tổ chức]** Đặt tên file tùy tiện (Document(1).pdf, baocao_final_final.docx) → không biết file gì tới khi mở.
2. **[Tổ chức]** Nhiều version cùng tài liệu (v1, v2, final, final_HOANCHINH) → không biết bản nào mới nhất.
3. **[Tổ chức]** File nằm sai chỗ (hợp đồng trong folder "New folder", SOP trộn với ảnh cá nhân).
4. **[Tổ chức]** File trùng lặp (download nhiều lần, copy nhầm nơi).
5. **[Tìm kiếm]** Tìm 1 tài liệu đã thấy mất nửa tiếng — phải nhớ tên file hoặc mở lần lượt.
6. **[Tìm kiếm]** Bắt đầu 1 dự án mới, không nhớ mình đã có tài liệu liên quan ở đâu → tìm lại từ đầu.
7. **[Tổ chức]** Khi đồng nghiệp xin file, phải tìm + gửi tay → mất thời gian, hay gửi nhầm bản cũ.
8. **[Tổ chức]** Không có "policy" đặt tên/thư mục → mỗi người tổ chức một kiểu, team không chia sẻ được.
9. **[Tìm kiếm]** Tài liệu tham khảo rải rác Google Drive + máy + email → không có nơi tập trung.
10. **[Tổ chức]** File cũ không biết có nên xóa → cứ giữ → folder phình to.

## Top use-case nên automate (GV tham khảo — KHÔNG cho HV trước)
- **#1 + #2 + #3 (tổ chức tài liệu):** Impact cao (cứu cả team hàng giờ/tuần), Difficulty trung (cần policy rõ + script copy). → **Quick win / Lên kế hoạch** = use-case CHÍNH demo BT2-BT6.
- **#5 + #6 (tìm kiếm tài liệu tham khảo):** Impact cao, Difficulty trung-thấp (AI search + rerank). → **Workflow mở rộng** (cuối lab).
- #4 (trùng lặp): difficulty thấp → làm cùng #1.
- #8 (policy): là tiền đề, phải làm trước khi automate.
