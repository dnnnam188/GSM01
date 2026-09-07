# Hướng dẫn deploy — GSM-01

> Kiến trúc: **Frontend Next.js trên Vercel** + **Backend FastAPI trên Render** +
> **PostgreSQL trên Neon** (ADR-002). Toàn bộ dùng gói free.

## 0. Trước khi bắt đầu

Cơ sở dữ liệu production phải đi qua migration runner. Seed chỉ dành cho database staging/demo:

```bash
.venv/Scripts/python.exe -m src.backend.db.migrate
# PowerShell: chỉ chạy trên database staging/demo
$env:ALLOW_DEMO_SEED="true"; $env:ENVIRONMENT="staging"; .venv/Scripts/python.exe -m src.backend.db.seed
.venv/Scripts/python.exe -m src.backend.rag.indexer
```

⚠️ `seed.py` chạy `TRUNCATE` toàn bộ bảng nghiệp vụ và sẽ bị chặn trên production.
Không dùng `scripts.demo_reset` trên database thật.

## 1. Backend lên Render

1. Push code lên GitHub.
2. Vào [dashboard.render.com](https://dashboard.render.com) → **New → Blueprint** → trỏ vào repo.
   Render đọc `render.yaml` ở thư mục gốc.
3. Điền các biến môi trường bắt buộc được đánh dấu `sync: false`:

   | Biến | Bắt buộc | Lấy ở đâu |
   |---|---|---|
   | `DATABASE_URL` | Có | Neon → Connection string (giữ nguyên `?sslmode=require`) |
   | `GEMINI_API_KEY` | Có | https://aistudio.google.com/apikey |
   | `JWT_SECRET` | Có | Sinh **mới**: `python -c "import secrets; print(secrets.token_urlsafe(48))"` |
   | `CORS_ORIGINS` | Có | `https://<tên-app>.vercel.app` — điền sau khi deploy frontend |
   | `OPENROUTER_API_KEY` | Không | Để trống khi `FALLBACK_ENABLED=false` |
   | `FALLBACK_API_KEY` | Không | Để trống khi `FALLBACK_ENABLED=false` |

   Giữ các giá trị sau trong Render: `LLM_ROUTER_MODEL` và `LLM_ANSWER_MODEL` là
   `gemini-3.5-flash-lite`, `LLM_EMBEDDING_MODEL` là `gemini-embedding-001`,
   `GEMINI_RPM=15`, và `FALLBACK_ENABLED=false`. Quota 250.000 TPM / 500 RPD
   do Google áp dụng theo project, không nhập thành biến để tự thay đổi quota.

   ⚠️ **Đừng dùng lại `JWT_SECRET` của máy cá nhân.** Ứng dụng sẽ từ chối khởi động nếu
   `ENVIRONMENT=production` mà secret vẫn là giá trị mẫu trong `.env.example`.

4. Kiểm tra liveness: `curl https://<tên-app>.onrender.com/api/health` phải trả `{"status":"ok"}`.
   Render dùng readiness: `curl https://<tên-app>.onrender.com/api/ready` phải trả `{"status":"ready"}`.

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

Frontend lấy một WebSocket ticket ngắn hạn qua `POST /api/auth/ws-ticket` rồi gửi
ticket trong frame đầu tiên. Không đưa access token dài hạn vào URL WebSocket.

Chạy kịch bản đầu-cuối nhắm vào bản đã deploy:

```bash
$env:GSM_BASE="https://<app>.onrender.com"; $env:GSM_WS="wss://<app>.onrender.com";
$env:GSM_DEMO_PASSWORD="<staging-password>";
.venv/Scripts/python.exe -m tests.test_e2e_slice
```

Phải đạt đủ 29/29 phép kiểm (bao gồm cấp và dùng one-time WebSocket ticket).

## 3b. Chạy ở máy phát triển

**Trên Windows bắt buộc dùng `run_dev.py`**, không gọi thẳng `uvicorn`:

```bash
.venv/Scripts/python.exe run_dev.py
```

Uvicorn chọn `ProactorEventLoop` trên Windows, mà `psycopg` bản async không chạy được trên đó —
checkpointer Postgres của LangGraph sẽ hỏng mọi kết nối. Trên Linux (Render) vòng lặp mặc định
vốn đã đúng, nên production cứ dùng `startCommand` trong `render.yaml` như bình thường.

## 4. Bẫy đã biết

| Vấn đề | Xử lý |
|---|---|
| **Render free tier ngủ sau ~15 phút** không có request. Lần gọi đầu mất 30–60 giây để dậy. | Mở trang trước buổi demo 5 phút, hoặc ping `/api/health` trước khi trình bày. Đây là nguyên nhân số một làm hỏng demo. |
| Gemini hết hạn mức gói free | Client tự giãn nhịp ở 15 RPM. Hiện `FALLBACK_ENABLED=false`, nên khi Gemini hết quota hệ thống trả lời suy giảm an toàn; chỉ bật fallback sau khi đã kiểm chứng provider mới. |
| WebSocket không kết nối được | Kiểm tra dùng `wss://` (không phải `ws://`) và `CORS_ORIGINS` khớp đúng domain Vercel. |
| Neon ngắt kết nối nhàn rỗi | Kết nối được mở theo từng request rồi đóng, nên không giữ kết nối chết. |
| `TTFT > 3s` sau khi deploy | Kiểm `LLM_ANSWER_MODEL` phải là `gemini-3.5-flash-lite` (ADR-010). Đọc `model_name` trong bảng `messages` để biết bản deploy đang dùng model nào. |
| Khách không nhận được kết quả duyệt HITL | Sổ kết nối WebSocket nằm trong bộ nhớ một tiến trình. Chạy nhiều worker là hỏng — giữ **một** worker, hoặc đổi `api/hub.py` sang pub/sub. |
| Bảng `checkpoints` không tồn tại | `get_checkpointer()` tự gọi `setup()` lần đầu. Nếu user DB không có quyền tạo bảng thì phải cấp quyền. |
