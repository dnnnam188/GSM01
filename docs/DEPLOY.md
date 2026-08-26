# Hướng dẫn deploy — GSM-01

> Kiến trúc: **Frontend Next.js trên Vercel** + **Backend FastAPI trên Render** +
> **PostgreSQL trên Neon** (ADR-002). Toàn bộ dùng gói free.

## 0. Trước khi bắt đầu

Cơ sở dữ liệu đã sẵn sàng — schema và seed đã chạy trên Neon. Nếu cần dựng lại từ đầu:

```bash
.venv/Scripts/python.exe -m src.backend.db.apply_schema
.venv/Scripts/python.exe -m src.backend.db.seed
.venv/Scripts/python.exe -m src.backend.rag.indexer
```

⚠️ `seed.py` chạy `TRUNCATE` toàn bộ bảng nghiệp vụ. Đừng chạy trên dữ liệu thật.

## 1. Backend lên Render

1. Push code lên GitHub.
2. Vào [dashboard.render.com](https://dashboard.render.com) → **New → Blueprint** → trỏ vào repo.
   Render đọc `render.yaml` ở thư mục gốc.
3. Điền 5 biến môi trường được đánh dấu `sync: false`:

   | Biến | Lấy ở đâu |
   |---|---|
   | `DATABASE_URL` | Neon → Connection string (giữ nguyên `?sslmode=require`) |
   | `GEMINI_API_KEY` | https://aistudio.google.com/apikey |
   | `OPENROUTER_API_KEY` | https://openrouter.ai/keys |
   | `JWT_SECRET` | Sinh **mới**: `python -c "import secrets; print(secrets.token_urlsafe(48))"` |
   | `CORS_ORIGINS` | `https://<tên-app>.vercel.app` — điền sau khi deploy frontend |

   ⚠️ **Đừng dùng lại `JWT_SECRET` của máy cá nhân.** Ứng dụng sẽ từ chối khởi động nếu
   `ENVIRONMENT=production` mà secret vẫn là giá trị mẫu trong `.env.example`.

4. Kiểm tra: `curl https://<tên-app>.onrender.com/api/health` phải trả `{"status":"ok"}`.

## 2. Frontend lên Vercel

1. [vercel.com/new](https://vercel.com/new) → import repo → **Root Directory: `src/frontend`**.
2. Đặt biến môi trường:

   | Biến | Giá trị |
   |---|---|
   | `NEXT_PUBLIC_API_BASE` | `https://<tên-app>.onrender.com` |
   | `NEXT_PUBLIC_WS_BASE` | `wss://<tên-app>.onrender.com` |

   `wss://` chứ không phải `ws://` — trang chạy HTTPS thì trình duyệt chặn WebSocket không mã hoá.

3. Deploy xong, quay lại Render cập nhật `CORS_ORIGINS` thành đúng domain Vercel vừa nhận.

## 3. Kiểm chứng sau deploy

Chạy kịch bản đầu-cuối nhắm vào bản đã deploy:

```bash
GSM_BASE=https://<app>.onrender.com GSM_WS=wss://<app>.onrender.com \
  .venv/Scripts/python.exe -m tests.test_e2e_slice
```

Phải đạt đủ 28/28 phép kiểm.

## 4. Bẫy đã biết

| Vấn đề | Xử lý |
|---|---|
| **Render free tier ngủ sau ~15 phút** không có request. Lần gọi đầu mất 30–60 giây để dậy. | Mở trang trước buổi demo 5 phút, hoặc ping `/api/health` trước khi trình bày. Đây là nguyên nhân số một làm hỏng demo. |
| Gemini hết hạn mức gói free | Hệ thống tự rơi sang OpenRouter (ADR-001). Đảm bảo `OPENROUTER_API_KEY` có trên Render, nếu không agent sẽ chỉ xin lỗi. |
| WebSocket không kết nối được | Kiểm tra dùng `wss://` (không phải `ws://`) và `CORS_ORIGINS` khớp đúng domain Vercel. |
| Neon ngắt kết nối nhàn rỗi | Kết nối được mở theo từng request rồi đóng, nên không giữ kết nối chết. |
| `TTFT > 3s` sau khi deploy | Đo lại khi hạn mức Gemini còn: fallback OpenRouter chậm hơn Gemini đáng kể. |
