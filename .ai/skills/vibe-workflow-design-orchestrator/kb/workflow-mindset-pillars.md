# 4 Trụ cột Workflow Mindset — Reference

> Nguồn: Webinar "Workflow Mindset: Thiết kế quy trình đáng tin cậy trước khi tự động hoá".

## 1. Value stream (IPO)
Mọi quy trình = **Input → Process → Output**. Đo giá trị mỗi bước: bước nào không tạo giá trị → Eliminate (E).

## 2. Ma trận Hiệu quả × Độ phức tạp
| | Độ phức tạp THẤP | Độ phức tạp CAO |
|---|---|---|
| **Hiệu quả CAO** | ⭐ QUICK WIN — automate trước | Đầu tư dài hạn |
| **Hiệu quả THẤP** | Làm tay / bỏ | Tránh |

Quick win = giá trị cao + dễ → chọn automate ĐẦU TIÊN để có momentum.

## 3. Quy trình đáng tin cậy — 6 thuộc tính
- **fault-tolerant** — có fallback khi lỗi
- **observable** — log đầy đủ, nhìn thấy đang chạy ra sao
- **scalable** — chịu được khối lượng lớn / batch
- **workable** — đơn giản, AI/ người thực sự làm được
- **idempotent** — chạy lại không sinh kết quả trùng/lệch
- **auditable** — trace được mỗi hành động

Thiếu thuộc tính nào → honest đánh "một phần/thiếu", KHÔNG overclaim "6/6 đạt" nếu chưa đủ.

## 4. Mô tả & trực quan hoá (Mermaid)
- Node AI → màu xanh
- Node HITL → màu đỏ
- ≤8 node (gộp bước nếu quá nhiều)
- Render thử trên mermaid.live trước khi dùng

## 3 nhánh automation (cho bước A)
- **n8n:** quy tắc rõ, kết nối hệ thống (email/Sheet/API)
- **AI Agent (Claude Code/Codex/Antigravity/OpenClaw/Hermes):** suy luận, đọc file, quyết định phi cấu trúc
- **App vibe coding:** giao diện nội bộ cho đội

## Quy tắc vàng (BR-W2)
Bước tiền bạc / PII / quyết định ảnh hưởng người dùng → **KHÔNG tự động hoàn toàn**, bắt buộc HITL.

## Use-case minh hoạ dumb/simple
**Tổ chức tài liệu** (folder lộn xộn → chuẩn hoá tên → tham chiếu policy → user review plan → AI Agent script copy file)
và **Tìm kiếm tài liệu tham khảo** (nội dung → keyword → search → rerank → reference_map.md).
KHÔNG mention skill nội bộ / DEVONthink — dùng ngữ cảnh trung tính (folder máy/Google Drive + AI Agent + script Python).
