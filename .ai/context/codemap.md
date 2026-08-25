# Code Map (Bản Đồ Mã Nguồn)

> 🎯 **Mục đích**: Trả lời nhanh câu hỏi *"Muốn sửa X thì mở file nào?"* để Agent không phải quét cả repo.
> Đây là file tiết kiệm token nhất trong `.ai/` — hãy giữ nó luôn cập nhật.
>
> 🔄 **Khi nào cập nhật**: mỗi khi thêm file mới, đổi tên file, hoặc di chuyển một khối logic lớn.

## 1. Điểm Vào Của Dự Án (Entry Points)

| Loại | Đường dẫn | Mô tả |
|---|---|---|
| Khởi động ứng dụng | `[ví dụ: index.html / src/main.ts]` | [Điểm chạy đầu tiên] |
| Cấu hình | `[ví dụ: package.json / vite.config.ts]` | [Cấu hình build & script] |
| Biến môi trường | `.env.example` | [Danh sách biến cần thiết] |

## 2. Bản Đồ Tính Năng → Mã Nguồn

> Cột "Vị trí" nên chỉ tới **file + hàm/khối cụ thể**, không chỉ tên thư mục.

| Tính năng / Vùng | Vị trí (file → hàm hoặc vùng dòng) | Ghi chú |
|---|---|---|
| [Tên tính năng 1] | `[đường/dẫn.ext]` → `[tenHam()]` | [Lưu ý khi sửa] |
| [Tên tính năng 2] | `[đường/dẫn.ext]` → `[tenHam()]` | |
| [Giao diện / CSS] | `[đường/dẫn]` | |
| [Dữ liệu / State] | `[đường/dẫn]` → `[tenBien]` | |
| [Tiện ích dùng chung] | `[đường/dẫn]` | |

## 3. Luồng Dữ Liệu Chính

```text
[Nguồn dữ liệu]  →  [Xử lý / State]  →  [Render / Đầu ra]
     ...                  ...                 ...
```

*[Mô tả ngắn 3–5 dòng: dữ liệu đi từ đâu, biến đổi ở đâu, hiển thị ra sao.]*

## 4. Vùng Nhạy Cảm – Sửa Cẩn Thận ⚠️

> Liệt kê các file/khối dễ vỡ, file quá lớn, hoặc có ràng buộc ẩn.

| Vị trí | Vì sao nhạy cảm | Cách xử lý an toàn |
|---|---|---|
| `[đường/dẫn]` | [ví dụ: file rất lớn, chứa dữ liệu nhúng trên một dòng] | [ví dụ: không đọc toàn bộ; dùng sed theo vùng dòng] |

## 5. Nơi KHÔNG Được Sửa Tay

- `node_modules/`, `dist/`, `build/`, `.next/` — sản phẩm sinh tự động.
- `[các file sinh tự động khác của dự án]`
