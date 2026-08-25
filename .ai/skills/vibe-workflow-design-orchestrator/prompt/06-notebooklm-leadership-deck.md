# Prompt BT6 — NotebookLM deck: Tham mưu lãnh đạo 30 ngày (CRAFT)

> Mục đích: Dùng NotebookLM generate deck thuyết trình tham mưu lãnh đạo triển khai workflow trong 30 ngày.
> Chạy tại: NotebookLM (notebooklm.google.com).
> Trước khi chạy: tạo notebook mới → Add source → dán design doc (BT2-BT3) + Mermaid (BT4).
>
> ⚠️ **Local-first / bảo mật:** NotebookLM là cloud Google. Nếu công ty cấm đẩy tài liệu lên cloud (hợp đồng, PII, tài liệu mật) → **KHÔNG dùng NotebookLM**. Thay vào đó: dán design doc + Mermaid vào Claude/Gemini + template PPTX Alobase (`slides/slides-webinar3-v2.pptx`) để vẽ deck local. BT6 là **OPTIONAL** — prompt CRAFT vẫn hợp lệ cho mọi tool.

```text
C — CONTEXT
Đây là deck thuyết trình THAM MƯU LÃNH ĐẠO triển khai 1 workflow AI Automation trong 30 ngày tới. Nguồn tài liệu đã add vào notebook: Workflow Design Doc (as-is, to-be ESIA, hardening) + Mermaid diagram. Đối tượng nghe: ban giám đốc / lãnh đạo phòng ban — người ra quyết định ngân sách, quan tâm ROI và rủi ro, không quan tâm chi tiết kỹ thuật.

R — ROLE
Bạn là Strategy Manager + Transformation Consultant. Viết deck thuyết trình thuyết minh ý tưởng bằng giọng rõ ràng, tự tin, dữ liệu dẫn dắt. Tránh jargon kỹ thuật; nếu dùng thuật ngữ (workflow, HITL, ESIA) phải giải thích 1 câu.

A — ACTION
Tạo 1 deck slide (7-10 slide) theo cấu trúc:
1. Cover: "Đề xuất triển khai AI Automation: [Tên workflow] — Tham mưu 30 ngày".
2. Vấn đề: pain point hiện tại (dùng as-is, có số liệu thời gian/lỗi nếu có).
3. Quy trình mới: tóm tắt to-be (3-5 điểm thay đổi chính + Mermaid diagram).
4. Lợi ích đo được: trước → sau (thời gian, chi phí, chất lượng).
5. Độ tin cậy production: 4 lớp hardening (fallback/log/edge/HITL) — giải thích ngắn vì sao lãnh đạo yên tâm.
6. Lộ trình 30 ngày: tuần 1 (pilot) → tuần 2 (hardening) → tuần 3 (chạy thử) → tuần 4 (go-live + monitoring).
7. Rủi ro & giảm thiểu: 3 rủi ro chính + cách xử lý.
8. nguồn lực cần: người, tool, ngân sách (ước lượng thận trọng).
9. Quyết định cần lãnh đạo: 2-3 decision ask rõ ràng.
10. Next step + liên hệ.

F — FORMAT
- 7-10 slide, mỗi slide 1 ý chính + 3-4 bullet ngắn + 1 visual (diagram/icon/chart).
- Font sans-serif lớn, đủ đọc từ xa.
- Số liệu có đơn vị (giờ, VND, %). Không bịa — nếu thiếu số, ghi "[cần đo]".
- Có chỗ chèn ảnh Mermaid/infographic.

T — TONE / TARGET
- Giọng tiếng Việt chuyên nghiệp, tự tin, không khoa trương, không doom.
- Audience: ban giám đốc non-tech nhưng am hiểu kinh doanh.
- Complexity: executive level — chiến lược + ROI, không code.
```

> **Cách chạy:** Tạo notebook → Add sources (design doc + Mermaid) → dán prompt trên vào chat → NotebookLM generate deck → download/export. Chỉnh tiêu đề + số liệu lợi ích cho đúng doanh nghiệp bạn.
