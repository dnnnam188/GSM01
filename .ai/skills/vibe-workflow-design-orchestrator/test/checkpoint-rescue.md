# Checkpoint rescue map

Khi user stuck ở pha X → xem sample tương ứng + checkpoint:

| Stuck ở | Sample fallback | Gợi ý |
|---------|-----------------|-------|
| W1 không nghĩ ra use-case | `synthetic-data/sample-problems-list.md` | Dùng 10 vấn đề công ty giả "Đông Dương Thương Mại" |
| W2 as-is thiếu bước | `synthetic-data/sample-as-is.md` | Mở rộng: không chỉ "làm", mà cả "đợi/chuyển tay/check lại" |
| W2 to-be đánh A hết | — | Quy tắc vàng: bước tiền bạc/PII → HITL, không A hoàn toàn |
| W3 không biết hardening gì | `synthetic-data/sample-design-doc.md` (mục 3) | 4 lớp: fallback/log/edge/HITL — từng bước Automate đều cần |
| W4 Mermaid lỗi | `synthetic-data/sample-mermaid.mmd` | Paste mermaid.live, ≤8 node, gộp bước |
| W5 chữ tiếng Việt lỗi font | — | Đổi prompt: "label tiếng Việt, font không dấu hoặc Unicode" |
| W6 deck chung chung | — | CRAFT 5 phần, lợi ích phải đo được hoặc [cần đo] |
