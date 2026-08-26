-- =====================================================================
-- GSM-01 — Schema PostgreSQL (Neon) + pgvector
-- Task: T-002 · Ngày: 2026-08-26
-- Áp dụng: .venv/Scripts/python -m src.backend.db.apply_schema
--
-- Quy ước (ADR-007): mọi tên bảng/cột dùng snake_case.
-- Trạng thái & enum dùng TEXT + CHECK thay vì native ENUM để còn sửa
-- được trong sprint mà không phải viết migration riêng.
-- =====================================================================

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ---------------------------------------------------------------------
-- 1. users — hai vai trò: khách hàng và nhân viên CSKH
--    ⚠️ full_name / phone là PII: mọi truy vấn phục vụ LLM phải đi qua
--    pii/tokenizer trước khi vào context (ADR-004).
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email           TEXT        NOT NULL UNIQUE,
    password_hash   TEXT        NOT NULL,
    role            TEXT        NOT NULL CHECK (role IN ('customer', 'agent')),
    full_name       TEXT        NOT NULL,
    phone           TEXT,
    membership_tier TEXT        NOT NULL DEFAULT 'STANDARD'
                                CHECK (membership_tier IN ('STANDARD', 'SILVER', 'GOLD', 'PLATINUM')),
    is_active       BOOLEAN     NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------
-- 2. drivers — tài xế (dữ liệu mô phỏng)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS drivers (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    full_name      TEXT        NOT NULL,
    phone          TEXT        NOT NULL,
    service_type   TEXT        NOT NULL CHECK (service_type IN ('BIKE', 'GREENCAR', 'LUXURY')),
    plate_number   TEXT        NOT NULL,
    rating_avg     NUMERIC(2,1) NOT NULL DEFAULT 5.0 CHECK (rating_avg BETWEEN 1.0 AND 5.0),
    total_trips    INTEGER     NOT NULL DEFAULT 0,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------
-- 3. rides — chuyến đi
--    quoted_fare vs final_fare  → phát hiện chênh lệch cước (case F).
--    planned_distance_km vs actual_distance_km → phát hiện đi vòng >30%.
--    idempotency_key → chống đặt trùng khi LLM gọi lại tool (ADR-005).
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS rides (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ride_code            TEXT        NOT NULL UNIQUE,
    customer_id          UUID        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    driver_id            UUID        REFERENCES drivers(id) ON DELETE SET NULL,
    service_type         TEXT        NOT NULL CHECK (service_type IN ('BIKE', 'GREENCAR', 'LUXURY')),
    status               TEXT        NOT NULL CHECK (status IN
                             ('PENDING', 'ASSIGNED', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED')),
    pickup_address       TEXT        NOT NULL,   -- PII
    dropoff_address      TEXT        NOT NULL,   -- PII
    planned_distance_km  NUMERIC(6,2),
    actual_distance_km   NUMERIC(6,2),
    quoted_fare          INTEGER,                -- VND, giá hiển thị lúc khách xác nhận
    final_fare           INTEGER,                -- VND, số tiền thực trừ
    cancel_fee           INTEGER     NOT NULL DEFAULT 0,
    cancel_reason        TEXT,
    cancelled_by         TEXT        CHECK (cancelled_by IN ('CUSTOMER', 'DRIVER', 'SYSTEM')),
    payment_method       TEXT        NOT NULL DEFAULT 'CASH'
                                     CHECK (payment_method IN ('CASH', 'CARD', 'WALLET')),
    idempotency_key      TEXT        UNIQUE,
    requested_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    started_at           TIMESTAMPTZ,
    completed_at         TIMESTAMPTZ,
    cancelled_at         TIMESTAMPTZ,
    CONSTRAINT rides_cancel_consistency CHECK (
        (status = 'CANCELLED' AND cancelled_at IS NOT NULL)
        OR (status <> 'CANCELLED' AND cancelled_at IS NULL)
    )
);
CREATE INDEX IF NOT EXISTS idx_rides_customer_time ON rides (customer_id, requested_at DESC);
CREATE INDEX IF NOT EXISTS idx_rides_status ON rides (status);

-- ---------------------------------------------------------------------
-- 4. ride_events — dòng thời gian của chuyến (dùng để agent giải thích
--    "vì sao bị tính phí này" thay vì phán đoán)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ride_events (
    id         BIGSERIAL PRIMARY KEY,
    ride_id    UUID        NOT NULL REFERENCES rides(id) ON DELETE CASCADE,
    event_type TEXT        NOT NULL CHECK (event_type IN
                   ('REQUESTED', 'DRIVER_ASSIGNED', 'DRIVER_ARRIVED', 'STARTED',
                    'ROUTE_DEVIATION', 'WAITING_STARTED', 'COMPLETED', 'CANCELLED', 'VEHICLE_ISSUE')),
    payload    JSONB       NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_ride_events_ride ON ride_events (ride_id, created_at);

-- ---------------------------------------------------------------------
-- 5. payments — mỗi lần trừ tiền là một dòng.
--    Hai dòng SUCCESS cùng ride_id = case thu tiền trùng (double charge).
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS payments (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ride_id         UUID        NOT NULL REFERENCES rides(id) ON DELETE CASCADE,
    customer_id     UUID        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    amount          INTEGER     NOT NULL,
    method          TEXT        NOT NULL CHECK (method IN ('CASH', 'CARD', 'WALLET')),
    status          TEXT        NOT NULL CHECK (status IN ('SUCCESS', 'FAILED', 'REFUNDED')),
    transaction_ref TEXT        NOT NULL UNIQUE,
    charged_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_payments_ride ON payments (ride_id);

-- ---------------------------------------------------------------------
-- 6. conversations — một phiên hội thoại.
--    thread_id là khoá để resume LangGraph sau HITL (ADR-003).
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS conversations (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id      UUID        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    thread_id        TEXT        NOT NULL UNIQUE,
    status           TEXT        NOT NULL DEFAULT 'ACTIVE'
                                 CHECK (status IN ('ACTIVE', 'WAITING_HUMAN', 'CLOSED')),
    rolling_summary  TEXT,
    started_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_activity_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_conversations_customer ON conversations (customer_id, last_activity_at DESC);

-- ---------------------------------------------------------------------
-- 7. messages — từng lượt.
--    ttft_ms là chỉ số nghiệm thu ràng buộc "< 3s" của đề bài,
--    KHÔNG phải latency_ms (thời gian trả xong).
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS messages (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id   UUID        NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role              TEXT        NOT NULL CHECK (role IN ('user', 'assistant', 'system', 'human_agent')),
    content           TEXT        NOT NULL,
    intent            TEXT        CHECK (intent IN (
                          'booking.create', 'booking.cancel', 'booking.modify', 'trip.lookup',
                          'fare.inquiry', 'refund.request', 'complaint.driver',
                          'complaint.lost_item', 'policy.faq', 'other')),
    intent_confidence NUMERIC(4,3),
    model_name        TEXT,
    -- KHÔNG ràng buộc danh sách provider: tên provider dự phòng do biến môi
    -- trường FALLBACK_PROVIDER_NAME quyết định (OpenRouter, AgentRouter, ...).
    -- Ràng buộc cứng ở đây từng khiến việc đổi provider làm vỡ bước ghi tin nhắn.
    provider          TEXT,
    prompt_tokens     INTEGER,
    completion_tokens INTEGER,
    ttft_ms           INTEGER,
    latency_ms        INTEGER,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages (conversation_id, created_at);
CREATE INDEX IF NOT EXISTS idx_messages_intent ON messages (intent) WHERE intent IS NOT NULL;

-- ---------------------------------------------------------------------
-- 8. tool_calls — BẢNG HẠNG NHẤT, không phải log file.
--    idempotency_key UNIQUE là tầng chống-gọi-trùng duy nhất không phụ
--    thuộc vào việc LLM cư xử đúng (ADR-005).
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS tool_calls (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID        REFERENCES conversations(id) ON DELETE CASCADE,
    message_id      UUID        REFERENCES messages(id) ON DELETE SET NULL,
    tool_name       TEXT        NOT NULL,
    arguments       JSONB       NOT NULL DEFAULT '{}'::jsonb,
    result          JSONB,
    status          TEXT        NOT NULL CHECK (status IN ('SUCCESS', 'ERROR', 'REPLAYED')),
    error_type      TEXT        CHECK (error_type IN ('RETRYABLE', 'FATAL', 'NEEDS_HUMAN')),
    error_message   TEXT,
    idempotency_key TEXT        UNIQUE,
    attempt         INTEGER     NOT NULL DEFAULT 1,
    latency_ms      INTEGER,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT tool_calls_error_shape CHECK (
        (status = 'ERROR' AND error_type IS NOT NULL)
        OR (status <> 'ERROR' AND error_type IS NULL)
    )
);
CREATE INDEX IF NOT EXISTS idx_tool_calls_conversation ON tool_calls (conversation_id, created_at);
CREATE INDEX IF NOT EXISTS idx_tool_calls_tool_status ON tool_calls (tool_name, status);

-- ---------------------------------------------------------------------
-- 9. tickets — khiếu nại
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS tickets (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ticket_code       TEXT        NOT NULL UNIQUE,
    customer_id       UUID        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    ride_id           UUID        REFERENCES rides(id) ON DELETE SET NULL,
    conversation_id   UUID        REFERENCES conversations(id) ON DELETE SET NULL,
    category          TEXT        NOT NULL CHECK (category IN
                          ('DRIVER_CONDUCT', 'LOST_ITEM', 'FARE_DISPUTE', 'SAFETY', 'OTHER')),
    severity          TEXT        NOT NULL DEFAULT 'NORMAL'
                                  CHECK (severity IN ('LOW', 'NORMAL', 'HIGH', 'CRITICAL')),
    status            TEXT        NOT NULL DEFAULT 'OPEN'
                                  CHECK (status IN ('OPEN', 'IN_PROGRESS', 'RESOLVED', 'REJECTED')),
    description       TEXT        NOT NULL,
    assigned_agent_id UUID        REFERENCES users(id) ON DELETE SET NULL,
    idempotency_key   TEXT        UNIQUE,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    resolved_at       TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_tickets_status ON tickets (status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_tickets_category ON tickets (category);

-- ---------------------------------------------------------------------
-- 10. refund_requests — trung tâm của luồng HITL.
--     status = 'PENDING_HITL' là hàng đợi chờ CSKH duyệt.
--     resume_thread_id để đánh thức đúng graph đang bị interrupt (ADR-003).
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS refund_requests (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    refund_code      TEXT        NOT NULL UNIQUE,
    customer_id      UUID        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    ride_id          UUID        REFERENCES rides(id) ON DELETE SET NULL,
    ticket_id        UUID        REFERENCES tickets(id) ON DELETE SET NULL,
    conversation_id  UUID        REFERENCES conversations(id) ON DELETE SET NULL,
    amount           INTEGER     NOT NULL CHECK (amount > 0),
    reason_code      TEXT        NOT NULL CHECK (reason_code IN
                         ('DOUBLE_CHARGE', 'ROUTE_INEFFICIENCY', 'FARE_DISCREPANCY',
                          'WRONG_CANCEL_FEE', 'SERVICE_INTERRUPTION', 'OTHER')),
    reason_detail    TEXT,
    fraud_score      NUMERIC(4,3) NOT NULL DEFAULT 0.0 CHECK (fraud_score BETWEEN 0 AND 1),
    status           TEXT        NOT NULL CHECK (status IN
                         ('AUTO_APPROVED', 'PENDING_HITL', 'APPROVED', 'REJECTED')),
    decided_by       UUID        REFERENCES users(id) ON DELETE SET NULL,
    decision_reason  TEXT,
    resume_thread_id TEXT,
    idempotency_key  TEXT        UNIQUE,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    decided_at       TIMESTAMPTZ,
    -- Từ chối thì bắt buộc có lý do (F12). Ràng buộc ở DB để giao diện
    -- không thể "quên" áp dụng.
    CONSTRAINT refund_reject_needs_reason CHECK (
        status <> 'REJECTED' OR (decision_reason IS NOT NULL AND length(trim(decision_reason)) > 0)
    ),
    -- Đã quyết định thì phải có người/thời điểm quyết định.
    CONSTRAINT refund_decision_shape CHECK (
        status = 'PENDING_HITL' OR decided_at IS NOT NULL
    )
);
CREATE INDEX IF NOT EXISTS idx_refunds_pending ON refund_requests (status, created_at)
    WHERE status = 'PENDING_HITL';

-- ---------------------------------------------------------------------
-- 11. audit_log — ai đã làm gì, khi nào, vì sao. Chỉ ghi thêm.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS audit_log (
    id          BIGSERIAL PRIMARY KEY,
    actor_type  TEXT        NOT NULL CHECK (actor_type IN ('AI_AGENT', 'HUMAN_AGENT', 'SYSTEM', 'CUSTOMER')),
    actor_id    UUID        REFERENCES users(id) ON DELETE SET NULL,
    action      TEXT        NOT NULL,
    entity_type TEXT        NOT NULL,
    entity_id   TEXT,
    before_data JSONB,
    after_data  JSONB,
    reason      TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_audit_entity ON audit_log (entity_type, entity_id, created_at DESC);

-- ---------------------------------------------------------------------
-- 12. business_config — NGƯỠNG NGHIỆP VỤ LÀ DỮ LIỆU, KHÔNG NẰM TRONG
--     PROMPT (ADR-006). Đổi ngưỡng ở đây có hiệu lực ngay lúc chạy.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS business_config (
    config_key  TEXT        PRIMARY KEY,
    config_value TEXT       NOT NULL,
    value_type  TEXT        NOT NULL CHECK (value_type IN ('int', 'float', 'bool', 'string', 'json')),
    description TEXT        NOT NULL,
    version     INTEGER     NOT NULL DEFAULT 1,
    updated_by  UUID        REFERENCES users(id) ON DELETE SET NULL,
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------
-- 13. knowledge_chunks — RAG store.
--     vector(768): gemini-embedding-001 mặc định trả 3072 chiều, nhưng
--     pgvector chỉ đánh index HNSW được tới 2000 chiều. Ép
--     outputDimensionality=768 khi gọi API — xem ADR-008.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS knowledge_chunks (
    id            BIGSERIAL PRIMARY KEY,
    source_file   TEXT        NOT NULL,
    heading       TEXT,
    chunk_index   INTEGER     NOT NULL,
    content       TEXT        NOT NULL,
    token_count   INTEGER,
    embedding     vector(768),
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (source_file, chunk_index)
);
CREATE INDEX IF NOT EXISTS idx_chunks_embedding ON knowledge_chunks
    USING hnsw (embedding vector_cosine_ops);

-- ---------------------------------------------------------------------
-- 14. csat_ratings — điểm hài lòng cuối phiên (F16)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS csat_ratings (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID        NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    customer_id     UUID        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    score           SMALLINT    NOT NULL CHECK (score BETWEEN 1 AND 5),
    comment         TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (conversation_id)
);
