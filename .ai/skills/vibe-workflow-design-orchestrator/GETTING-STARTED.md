# Getting Started — vibe-workflow-design-orchestrator

## 30 giây đầu tiên

1. Cài đặt (xem `INSTALL.md`).
2. Gọi skill: `/vibe-workflow-design-orchestrator`.
3. Nêu use-case: *"Tôi muốn tự động hoá quy trình [X]"* — hoặc chỉ cần nêu danh sách vấn đề,
   skill sẽ chọn quick win cho bạn.

## Pipeline 6 pha móc nối

```
W0 INTAKE → W1 USECASE MATRIX → W2 AS-IS/ESIA TO-BE → W3 HARDENING
        → W4 MERMAID → W5 INFOGRAPHIC → W6 LEADERSHIP DECK → W7 PACKAGE
```

Quy tắc cốt lõi: **output pha N = input pha N+1**. Mỗi pha có 1 prompt copy-paste
(3 phần: BỐI CẢNH / CHỈ DẪN / TIÊU CHUẨN) trong thư mục `prompt/`.

## 3 use case phổ biến

**1. Tôi có 1 quy trình muốn tự động hoá**
→ Bắt đầu W0 với use-case đó. Skill đi thẳng W1→W7.

**2. Tôi chỉ có "list vấn đề", chưa biết làm gì trước**
→ Chạy W1 (ma trận Hiệu quả × Độ phức tạp) → pick top-3 quick win → chọn 1 → W2.

**3. Tôi muốn dạy/học workflow design**
→ Dùng `synthetic-data/company-dong-duong-thuongmai.md` (công ty giả, zero PII) +
các `sample-*.md` làm fallback. Có `test/smoke-test.md` chạy đầy đủ W1→W7.

## Quy tắc vàng (KHÔNG thương lượng)

Bước sai hậu quả nặng — tiền bạc, dữ liệu cá nhân, quyết định ảnh hưởng người —
→ **BẮT BUỘC Human-in-the-loop**, KHÔNG tự động hoàn toàn.

## Không bịa số

Chưa đo → ghi `[cần đo]`. Schema ép mỗi claim phải có `evidence[]` + `confidence_score`.

## Cần tùy chỉnh?

- Use-case minh hoạ: thay công ty giả bằng use-case thật của bạn (W0 INTAKE).
- Nhánh automation (n8n / AI Agent / vibe coding app): chọn theo đặc tính bước ở W2.
- Không có placeholder brand màu/font — màu trong Mermaid là màu phân loại
  (AI = cam, HITL = đỏ, fallback = xám), giữ nguyên.
