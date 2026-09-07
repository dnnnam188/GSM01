# Data Model — GSM-01

- **Bootstrap schema**: `src/backend/db/schema.sql` · **Migration runner**: `src/backend/db/migrate.py`
  · **Seed staging**: `src/backend/db/seed.py`
- **Hạ tầng**: Neon PostgreSQL **17.11** + `pgvector` **0.8.0** (ADR-002)
- **Áp dụng**: `.venv/Scripts/python -m src.backend.db.migrate` (ghi nhận vào `schema_migrations`)
- **Nạp dữ liệu staging**: đặt `ALLOW_DEMO_SEED=true`, `ENVIRONMENT=staging` rồi chạy
  `.venv/Scripts/python -m src.backend.db.seed` (xoá sạch rồi nạp lại, kết quả tất định)

---

## 1. Mười bốn bảng

| # | Bảng | Vai trò | Điểm cần biết |
|---|---|---|---|
| 1 | `users` | Khách hàng + nhân viên CSKH | `role` ∈ `customer`/`agent`. `full_name`, `phone` là PII |
| 2 | `drivers` | Tài xế mô phỏng | `phone` là PII |
| 3 | `rides` | Chuyến đi | `quoted_fare` vs `final_fare`, `planned_distance_km` vs `actual_distance_km` — hai cặp cột này là cơ sở để phát hiện khiếu nại đúng/sai |
| 4 | `ride_events` | Dòng thời gian chuyến | Cho phép agent **giải thích** khoản phí thay vì phán đoán |
| 5 | `payments` | Mỗi lần trừ tiền một dòng | Hai dòng `SUCCESS` cùng `ride_id` = thu tiền trùng |
| 6 | `conversations` | Phiên hội thoại | `thread_id` là khoá resume LangGraph sau HITL |
| 7 | `messages` | Từng lượt | `ttft_ms` là chỉ số nghiệm thu "< 3s", **không phải** `latency_ms` |
| 8 | `tool_calls` | Nhật ký gọi tool | `idempotency_key UNIQUE` — xem mục 3 |
| 9 | `tickets` | Phiếu khiếu nại | |
| 10 | `refund_requests` | Trung tâm luồng HITL | `status='PENDING_HITL'` chính là hàng đợi CSKH |
| 11 | `audit_log` | Ai làm gì, khi nào, vì sao | Chỉ ghi thêm |
| 12 | `business_config` | Ngưỡng nghiệp vụ | ADR-006 — xem mục 4 |
| 13 | `knowledge_chunks` | Vector store cho RAG | `vector(768)` — xem mục 5 |
| 14 | `csat_ratings` | Điểm hài lòng 1–5 | Một phiên một điểm |

> Bảng `schema_migrations` và checkpoint của LangGraph do runtime/migration runner quản lý;
> checkpoint không khai báo trong `schema.sql`.

---

## 2. Quan hệ chính

```text
users(customer) ──< rides ──< ride_events
                     │  └───< payments
                     │
users(customer) ──< conversations ──< messages ──< tool_calls
                          │
                          ├──< tickets ──┐
                          └──< refund_requests ──> users(agent)  [decided_by]
                                                └─> audit_log
```

---

## 3. Ràng buộc được đẩy xuống tầng DB (đã kiểm chứng bằng lệnh thật)

Đây là các bảo đảm **không phụ thuộc vào việc LLM hay giao diện cư xử đúng**:

| Ràng buộc | Bảng | Chặn được gì | Kết quả thử |
|---|---|---|---|
| `idempotency_key UNIQUE` | `tool_calls`, `rides`, `tickets`, `refund_requests` | LLM gọi lại tool → hoàn tiền / đặt xe hai lần (ADR-005) | ✅ `duplicate key value violates unique constraint` |
| `refund_reject_needs_reason` | `refund_requests` | CSKH từ chối mà không nhập lý do (F12) | ✅ `violates check constraint` |
| `refund_decision_shape` | `refund_requests` | Đánh dấu đã duyệt nhưng thiếu thời điểm quyết định | — |
| `tool_calls_error_shape` | `tool_calls` | Ghi `status='ERROR'` mà bỏ trống `error_type` | — |
| `rides_cancel_consistency` | `rides` | Trạng thái `CANCELLED` mà thiếu `cancelled_at` | — |

---

## 4. `business_config` — 18 khoá

Ngưỡng nghiệp vụ là **dữ liệu đọc lúc chạy**, không nằm trong prompt (ADR-006).
Đổi giá trị ở đây có hiệu lực ngay — đó là cách kích hoạt luồng HITL trực tiếp khi demo.

Khoá quan trọng nhất:

| Khoá | Giá trị | Ý nghĩa |
|---|---|---|
| `refund.auto_approve_max_vnd` | `50000` | Trên mức này **bắt buộc** HITL |
| `refund.auto_approve_max_per_month` | `2` | Từ lần thứ 3 trong tháng đều phải qua người |
| `refund.fraud_score_hitl_threshold` | `0.5` | Nghi gian lận thì ép HITL dù tiền nhỏ |
| `cancel.free_window_seconds` | `120` | Cửa sổ huỷ miễn phí |
| `route.deviation_threshold_pct` | `30` | Vượt % này mới đủ điều kiện hoàn do đi vòng |
| `alert.daily_refund_cap_vnd` | `2000000` | Vượt thì cảnh báo trên dashboard (F14) |

> ⚠️ **Đồng bộ hai chiều**: mọi con số ở đây đều đối chiếu từ `data/knowledge_base/`.
> Sửa một nơi mà quên nơi kia thì agent trả lời một đằng, hệ thống xử một nẻo.
> Cột `description` của mỗi khoá ghi rõ file KB làm căn cứ.

---

## 5. Vector store

`knowledge_chunks.embedding` là `vector(768)`, index `hnsw (vector_cosine_ops)`.

**Vì sao 768 mà không phải mặc định**: `gemini-embedding-001` trả về **3072 chiều** nếu không
truyền tham số, nhưng index HNSW của pgvector chỉ hỗ trợ tới **2000 chiều**. Vì vậy phải ép
`outputDimensionality=768` ở mọi lời gọi embed. Cả hai con số này đã đo bằng key thật:

```
embed dim (mặc định)          : 3072
embed dim (outputDimensionality=768) : 768
```

Nếu đổi model embedding thì phải đổi cả `vector(N)` trong schema và index — đây là thay đổi
phá vỡ dữ liệu cũ, cần re-index toàn bộ kho tri thức.

---

## 6. Dữ liệu seed

**311 chuyến** (300 nền + 11 case cài sẵn), 52 người dùng, 20 tài xế.
`random.Random(42)` nên **mỗi lần seed cho kết quả giống hệt nhau** — điều kiện cần để bộ eval
ở T-008 so sánh được giữa các lần chạy.

### Tài khoản demo — mật khẩu chung `Demo@123`

| Email | Vai trò | Ghi chú |
|---|---|---|
| `demo.customer@gsm.vn` | `customer` | Sở hữu **toàn bộ** case khó bên dưới |
| `agent01@gsm.vn`, `agent02@gsm.vn` | `agent` | Nhân viên CSKH |
| `customer01..49@gsm.vn` | `customer` | Dữ liệu nền |

### Mười một case khó cài sẵn

Mỗi case có `ride_code` **cố định** để golden set và kịch bản demo trỏ thẳng vào:

| ride_code | Loại | Dùng để kiểm chứng điều gì |
|---|---|---|
| `XSM-DOUBLE-01` | Thu trùng 32.000đ | Dưới ngưỡng → AI **tự duyệt** |
| `XSM-DOUBLE-02` | Thu trùng 120.000đ | Trên ngưỡng → **bắt buộc HITL** (kịch bản demo chính) |
| `XSM-DETOUR-01` | Đi vòng +61,5% | Vượt ngưỡng 30% → đủ điều kiện hoàn |
| `XSM-DETOUR-02` | Đi vòng +13,9% | **Chưa đủ** ngưỡng → agent phải từ chối |
| `XSM-CANCELFEE-01` | Huỷ ở giây 74, vẫn thu 20.000đ | Thu phí **sai** → phải hoàn |
| `XSM-CANCELFEE-02` | Huỷ ở phút 6, thu 20.000đ | Thu phí **đúng** → agent phải từ chối |
| `XSM-LOSTITEM-01` | Hoàn thành 3 giờ trước | Còn trong hạn tìm đồ |
| `XSM-FAREDIFF-01` | Báo 85.000đ, trừ 127.000đ | Chênh lệch cước +49,4% |
| `XSM-VEHICLE-01` | Xe hết pin giữa đường | Gián đoạn dịch vụ |
| `XSM-ACTIVE-01` | Đang `IN_PROGRESS` | Cho `booking.modify` |
| `XSM-ACTIVE-02` | `ASSIGNED` 40 giây trước | Huỷ miễn phí được |

> Bốn cặp case **có/không đủ điều kiện** (`DOUBLE-01`/`02`, `DETOUR-01`/`02`, `CANCELFEE-01`/`02`)
> là phần giá trị nhất của seed: chúng kiểm tra agent có **từ chối đúng** hay không, chứ không chỉ
> kiểm tra agent có đồng ý đúng hay không. Agent nào cũng biết nói "vâng, em hoàn tiền cho anh".

### Truy vấn kiểm chứng

Bốn câu truy vấn dưới đây đã chạy thật trên Neon và trả đúng số dòng mong đợi:

```sql
-- Thu tiền trùng → XSM-DOUBLE-01, XSM-DOUBLE-02
SELECT r.ride_code, count(*) FROM payments p JOIN rides r ON r.id = p.ride_id
WHERE p.status = 'SUCCESS' GROUP BY r.ride_code HAVING count(*) > 1;

-- Đi vòng vượt ngưỡng (ngưỡng đọc từ business_config) → chỉ XSM-DETOUR-01
SELECT r.ride_code, round((r.actual_distance_km / r.planned_distance_km - 1) * 100, 1)
FROM rides r, business_config c
WHERE c.config_key = 'route.deviation_threshold_pct'
  AND r.actual_distance_km IS NOT NULL
  AND (r.actual_distance_km / r.planned_distance_km - 1) * 100 > c.config_value::numeric;

-- Thu phí huỷ sai → chỉ XSM-CANCELFEE-01
SELECT r.ride_code, extract(epoch FROM (r.cancelled_at - r.requested_at))::int, r.cancel_fee
FROM rides r, business_config c
WHERE c.config_key = 'cancel.free_window_seconds'
  AND r.status = 'CANCELLED' AND r.cancel_fee > 0
  AND extract(epoch FROM (r.cancelled_at - r.requested_at)) <= c.config_value::numeric;

-- Hàng đợi HITL → RF-SEED-0001, 120.000đ
SELECT refund_code, amount, reason_code, resume_thread_id
FROM refund_requests WHERE status = 'PENDING_HITL';
```
