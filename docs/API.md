# GSM-01 API

Base URL local: `http://127.0.0.1:8000`
Base URL staging/production: giá trị backend trong Render.

## Health

- `GET /api/health`: liveness, không kiểm tra dependency.
- `GET /api/ready`: readiness, kiểm tra PostgreSQL và trả `503` nếu database chưa sẵn sàng.

## Authentication

- `POST /api/auth/login`: nhận `{ "email": "...", "password": "..." }`, trả access token.
- `POST /api/auth/ws-ticket`: cần `Authorization: Bearer <access_token>`, chỉ customer được gọi.
  Trả ticket dùng một lần, sống ngắn hạn.
- `GET /api/me`: cần Bearer token.

Access token không được đưa vào URL WebSocket. Luồng chat:

1. Gọi `POST /api/auth/ws-ticket` bằng Bearer token.
2. Mở `wss://<backend>/ws/chat`.
3. Gửi frame đầu tiên: `{ "type": "auth", "ticket": "<one-time-ticket>" }`.
4. Chờ event `ready`, sau đó gửi `{ "message": "..." }`.

## Customer

- `POST /api/chat/{thread_id}/csat`
- `GET /api/chat/{thread_id}/csat`

## Agent

- `GET /api/dashboard/summary`
- `GET /api/dashboard/stats`
- `GET /api/hitl/queue`
- `POST /api/hitl/{refund_code}/decide`
- `GET /api/conversations/{conversation_id}/transcript`

Tất cả endpoint agent cần role `agent`. CSAT cần role `customer`.

## Error contract

- `400`: request không hợp lệ.
- `401`: thiếu hoặc hết hạn token/ticket.
- `403`: sai role hoặc Origin không được phép.
- `409`: thao tác HITL đã được xử lý trước đó.
- `422`: Pydantic validation.
- `429`: vượt rate limit; đọc header `Retry-After`.
- `503`: readiness dependency chưa sẵn sàng.

Mỗi response HTTP có `X-Request-ID` để đối chiếu log mà không cần ghi credential vào log.
