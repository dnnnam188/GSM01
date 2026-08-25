# Mẫu: ADR (Architecture Decision Record)

> Copy khối dưới đây, dán vào **đầu** danh sách trong `.ai/context/decisions.md`.
> Chỉ ghi ADR cho các quyết định **khó đảo ngược**: chọn thư viện lớn, chọn kiến trúc,
> chọn định dạng dữ liệu, hoặc cố ý **không** làm một việc gì đó.

---

## ADR-00X — [Tên quyết định ngắn gọn]

- **Ngày**: YYYY-MM-DD
- **Trạng thái**: `Đang áp dụng` | `Đã thay thế bởi ADR-00X` | `Đang cân nhắc`
- **Bối cảnh**: [Tình huống buộc phải ra quyết định]
- **Quyết định**: [Chốt làm theo cách nào]
- **Lý do**: [Vì sao chọn cách này]
- **Phương án đã loại**:
  - [Phương án A] — loại vì [lý do]
  - [Phương án B] — loại vì [lý do]
- **Hệ quả**: [Được gì, mất gì, ràng buộc phát sinh]

---

## Lưu ý khi viết

- Phần **"Phương án đã loại"** là phần giá trị nhất — nó ngăn agent phiên sau làm lại thứ đã bị loại.
- Không sửa nội dung ADR cũ khi đổi ý. Hãy ghi ADR mới và đánh dấu ADR cũ là `Đã thay thế bởi ADR-00X`.
