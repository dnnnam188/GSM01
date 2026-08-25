# Smoke test (~5 phút)

Chạy W1→W7 trên use-case synthetic "tổ chức tài liệu" (dùng `synthetic-data/company-dong-duong-thuongmai.md`).

**Pass khi:**
- [ ] W1: ma trận 4 góc + top-3 use-case
- [ ] W2: as-is ≥5 bước, to-be mỗi bước 1 ký hiệu E/S/I/A, ≥1 bước HITL
- [ ] W3: 4 lớp hardening đủ, 6 thuộc tính tự đánh giá (thẳng thắn, không ảo)
- [ ] W4: Mermaid render được, ≤8 node, ≥1 node HITL
- [ ] W5: prompt render ảnh có style spec + Mermaid source
- [ ] W6: deck có mục tiêu + lộ trình 30 ngày + ≥1 lợi ích đo được (hoặc [cần đo])
- [ ] W7: Design Doc 7 phần ráp đủ, validate schema PASS
- [ ] KHÔNG mention skill nội bộ/DEVONthink
- [ ] Slop CLEAN trên design doc (python3 slop_checker nếu có)
