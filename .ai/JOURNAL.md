# JOURNAL – Nhật Ký Bàn Giao Ca

> 🎯 **Mục đích**: Trả lời câu hỏi *"ĐÃ XẢY RA CHUYỆN GÌ?"* — file này là **nhật ký, chỉ thêm mới**.
> Việc *còn phải làm gì* nằm ở `.ai/TASKS.md`, đừng gộp hai thứ vào đây.
>
> 📋 **Định dạng**: dùng mẫu tại `.ai/templates/journal-entry.md`.
> 🔝 **Thứ tự**: entry mới nhất đặt **trên cùng**.
> 🔄 **Khi nào ghi**: cuối mỗi phiên làm việc, hoặc khi hoàn thành một task lớn.
>
> 👉 **Agent mới vào phiên**: đọc 3–5 entry gần nhất là đủ, không cần đọc hết file.

---

<!-- Thêm entry mới ngay dưới dòng này -->

## [2026-08-25] – Khởi tạo & Đối Soát Bộ Tri thức RAG Với Dữ Liệu Thực Tế Xanh SM
- **Agent / Người thực hiện**: Antigravity
- **Task liên quan**: T-001

### ✅ Đã làm được
- Thực hiện Search Web tra cứu thông tin niêm yết chính thức từ `xanhsm.com`, `greensm.com` và các kênh truyền thông chính thống.
- Cập nhật số liệu chuẩn xác 100% cho biểu phí: Xanh SM Bike (13.800đ/2km đầu, 4.800đ/km tiếp), GreenCar VF 5/e34 (30.500đ/2km đầu, 15.500đ/km tiếp), Luxury VF 8 (21.000đ/km), phụ phí đêm 22h-6h (10k/20k), phí chờ (60.000đ/h), phí thêm điểm dừng (10.000đ/điểm), Hotline 24/7 (1900 2088), email `support.vn@greensm.com`.
- Hoàn thiện trọn bộ 7 tài liệu Markdown chuẩn RAG trong `data/knowledge_base/`.

### 📁 File đã tạo
- `data/knowledge_base/01_pricing_and_surcharges.md` — Biểu phí & phụ phí chi tiết 3 dòng xe (Bike, GreenCar, Luxury)
- `data/knowledge_base/02_cancellation_and_fees.md` — Chính sách hủy chuyến, điều kiện miễn phí & phí No-Show
- `data/knowledge_base/03_refund_and_compensation.md` — Chính sách hoàn tiền, ngưỡng AI Auto-Refund vs CSKH HITL
- `data/knowledge_base/04_lost_and_found_policy.md` — Quy trình tìm kiếm đồ thất lạc và bảo mật SĐT
- `data/knowledge_base/05_driver_conduct_and_safety.md` — Chuẩn 5 sao và 3 cấp độ xử lý khiếu nại tài xế
- `data/knowledge_base/06_general_faq_and_features.md` — Hướng dẫn đặt đa điểm, đặt hộ, thú cưng, VAT e-invoice
- `data/knowledge_base/07_pii_and_privacy_policy.md` — Quy tắc ẩn danh PII và quy định bảo mật dữ liệu

### ⏳ Đang dở
- Task T-002: Thiết kế Database Schema (PostgreSQL) và Mock Seed Data.

### ⚠️ Vướng mắc / Cần con người quyết
- Không.

### ➡️ Việc tiếp theo
- Thiết kế Data Schema (PostgreSQL DDL) và Pydantic Schemas cho các Tool Function (T-002, T-003).
