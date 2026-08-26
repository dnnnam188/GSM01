"use client";

import { useCallback, useEffect, useState } from "react";
import { Shell } from "@/components/Shell";
import {
  decideRefund,
  fetchDashboard,
  fetchQueue,
  fetchTranscript,
  type DashboardSummary,
  type PendingCase,
  type Session,
  type Transcript,
} from "@/lib/api";
import { INTENT_LABEL, REASON_LABEL, money, ms, sinceNow, when } from "@/lib/format";

export function AgentDashboard({
  session,
  onLogout,
}: {
  session: Session;
  onLogout: () => void;
}) {
  const [tab, setTab] = useState("queue");
  const [queue, setQueue] = useState<PendingCase[] | null>(null);
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [error, setError] = useState("");

  const reload = useCallback(async () => {
    try {
      const [q, s] = await Promise.all([
        fetchQueue(session.accessToken),
        fetchDashboard(session.accessToken),
      ]);
      setQueue(q.pending);
      setSummary(s);
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không tải được dữ liệu");
    }
  }, [session.accessToken]);

  useEffect(() => {
    void reload();
  }, [reload]);

  return (
    <Shell
      session={session}
      onLogout={onLogout}
      tabs={[
        { id: "queue", label: "Chờ duyệt", count: queue?.length ?? 0 },
        { id: "stats", label: "Tổng quan" },
      ]}
      activeTab={tab}
      onTabChange={setTab}
    >
      {error && <p className="notice notice--danger">{error}</p>}

      {tab === "queue" ? (
        <QueueView
          token={session.accessToken}
          cases={queue}
          onDecided={reload}
        />
      ) : (
        <StatsView summary={summary} />
      )}
    </Shell>
  );
}

/* ------------------------------------------------------------------ */
function QueueView({
  token,
  cases,
  onDecided,
}: {
  token: string;
  cases: PendingCase[] | null;
  onDecided: () => void;
}) {
  const [openCase, setOpenCase] = useState<PendingCase | null>(null);

  if (cases === null) return <QueueSkeleton />;

  if (cases.length === 0) {
    return (
      <div className="panel">
        <div className="empty">
          <p className="empty__title">Không còn yêu cầu nào chờ duyệt</p>
          <p className="empty__hint">
            Các khoản hoàn tiền dưới hạn mức được trợ lý xử lý tự động. Chỉ những ca vượt
            hạn mức, nghi ngờ gian lận, hoặc vượt số lần cho phép trong tháng mới xuất
            hiện ở đây.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="split">
      <section className="panel panel--flush">
        <div className="queue">
          {cases.map((item, index) => (
            <CaseRow
              key={item.refund_code}
              index={index}
              item={item}
              token={token}
              selected={openCase?.refund_code === item.refund_code}
              onSelect={() => setOpenCase(item)}
              onDecided={() => {
                setOpenCase(null);
                onDecided();
              }}
            />
          ))}
        </div>
      </section>

      <section className="panel">
        {openCase ? (
          <TranscriptView token={token} item={openCase} />
        ) : (
          <div className="empty">
            <p className="empty__title">Chọn một ca để xem bằng chứng</p>
            <p className="empty__hint">
              Bảng bên phải hiển thị toàn bộ hội thoại và các bước trợ lý đã thực hiện,
              để bạn quyết định dựa trên dữ liệu chứ không phải phỏng đoán.
            </p>
          </div>
        )}
      </section>
    </div>
  );
}

function CaseRow({
  index,
  item,
  token,
  selected,
  onSelect,
  onDecided,
}: {
  index: number;
  item: PendingCase;
  token: string;
  selected: boolean;
  onSelect: () => void;
  onDecided: () => void;
}) {
  const [rejecting, setRejecting] = useState(false);
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState("");

  async function decide(approved: boolean) {
    if (!approved && !reason.trim()) {
      setFailure("Từ chối hoàn tiền bắt buộc phải nêu lý do");
      return;
    }
    setBusy(true);
    setFailure("");
    try {
      await decideRefund(token, item.refund_code, approved, approved ? null : reason.trim());
      onDecided();
    } catch (err) {
      setFailure(err instanceof Error ? err.message : "Không ghi được quyết định");
    } finally {
      setBusy(false);
    }
  }

  return (
    <article
      className="case"
      style={{
        ["--i" as string]: index,
        background: selected ? "var(--surface-sunken)" : undefined,
      }}
    >
      <div className="case__head">
        <span className="case__amount money">{money(item.amount)}</span>
        <span className="badge badge--warn">{REASON_LABEL[item.reason_code] ?? item.reason_code}</span>
        {item.fraud_score > 0 && (
          <span className="badge badge--danger">
            nghi ngờ {(item.fraud_score * 100).toFixed(0)}%
          </span>
        )}
      </div>

      <p style={{ margin: "6px 0 0", fontSize: 13, color: "var(--text-muted)" }}>
        {item.customer_name}
        {item.ride_code ? ` · chuyến ${item.ride_code}` : ""} · {sinceNow(item.created_at)}
      </p>

      {item.reason_detail && <p className="case__evidence">{item.reason_detail}</p>}

      <div className="case__actions">
        <button className="btn-approve" onClick={() => decide(true)} disabled={busy}>
          {busy ? "Đang ghi…" : "Duyệt hoàn tiền"}
        </button>
        <button
          className="btn-reject"
          onClick={() => setRejecting((value) => !value)}
          disabled={busy}
        >
          Từ chối
        </button>
        <button className="btn-quiet" onClick={onSelect}>
          {selected ? "Đang xem bằng chứng" : "Xem bằng chứng"}
        </button>
      </div>

      {rejecting && (
        <div className="reject-form">
          <label htmlFor={`reason-${item.refund_code}`}>
            Lý do từ chối — khách hàng sẽ đọc được nội dung này
          </label>
          <textarea
            id={`reason-${item.refund_code}`}
            rows={2}
            value={reason}
            onChange={(event) => setReason(event.target.value)}
            placeholder="Ví dụ: đối soát GPS cho thấy lộ trình đúng, không có dấu hiệu đi vòng"
          />
          <div className="row" style={{ marginTop: 10 }}>
            <button className="btn-reject" onClick={() => decide(false)} disabled={busy}>
              Xác nhận từ chối
            </button>
            <button className="btn-quiet" onClick={() => setRejecting(false)} disabled={busy}>
              Huỷ
            </button>
          </div>
        </div>
      )}

      {failure && (
        <p className="error-text" role="alert">
          {failure}
        </p>
      )}
    </article>
  );
}

/* ------------------------------------------------------------------ */
function TranscriptView({ token, item }: { token: string; item: PendingCase }) {
  const [data, setData] = useState<Transcript | null>(null);
  const [error, setError] = useState("");
  const conversationId = item.conversation_id ?? item.resume_thread_id;

  useEffect(() => {
    setData(null);
    if (!conversationId) {
      setError("Ca này không gắn với hội thoại nào");
      return;
    }
    fetchTranscript(token, conversationId)
      .then(setData)
      .catch((err) => setError(err instanceof Error ? err.message : "Không tải được"));
  }, [token, conversationId]);

  if (error) return <p className="notice notice--danger">{error}</p>;
  if (!data) return <TranscriptSkeleton />;

  return (
    <div className="stack">
      <div>
        <p className="section-title">Hội thoại · {item.refund_code}</p>
        <div className="thread" style={{ minHeight: 0, maxHeight: "34vh" }}>
          {data.messages.map((message, index) => (
            <div
              key={index}
              className={`turn turn--${message.role === "user" ? "me" : "bot"}`}
            >
              <div className="bubble">{message.content}</div>
              <div className="turn__meta">
                {message.intent && (
                  <span className="badge">{INTENT_LABEL[message.intent] ?? message.intent}</span>
                )}
                <span className="tnum">{when(message.created_at)}</span>
                {message.ttft_ms ? <span className="tnum">{ms(message.ttft_ms)}</span> : null}
              </div>
            </div>
          ))}
        </div>
      </div>

      <div>
        <p className="section-title">
          Trợ lý đã làm gì · {data.tool_calls.length} bước
        </p>
        {data.tool_calls.length === 0 ? (
          <p className="empty__hint">Chưa có bước nào được ghi lại.</p>
        ) : (
          <div className="trace">
            {data.tool_calls.map((call, index) => (
              <div className="trace__row" key={index}>
                <span
                  className={`trace__dot${call.status === "SUCCESS" ? "" : " trace__dot--err"}`}
                  aria-hidden
                />
                <div>
                  <div className="mono" style={{ color: "var(--text)" }}>
                    {call.tool_name}
                    {call.error_type ? ` · ${call.error_type}` : ""}
                  </div>
                  <div className="mono trace__args">{summarise(call.arguments)}</div>
                </div>
                <span className="trace__ms mono">{ms(call.latency_ms)}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
function StatsView({ summary }: { summary: DashboardSummary | null }) {
  if (!summary) return <QueueSkeleton />;

  const overBudget = summary.ttft_p95_ms !== null && summary.ttft_p95_ms >= 3000;
  const intents = Object.entries(summary.messages_by_intent).sort((a, b) => b[1] - a[1]);
  const busiest = intents[0]?.[1] ?? 1;

  return (
    <div className="stack">
      <div className="metrics">
        <Metric value={summary.pending_hitl} label="Chờ duyệt hoàn tiền" />
        <Metric value={summary.open_tickets} label="Ticket đang mở" />
        <Metric value={summary.total_messages} label="Tin nhắn đã xử lý" />
        <Metric value={summary.tool_calls} label="Lượt gọi công cụ" />
        <Metric
          value={summary.ttft_p95_ms ? ms(summary.ttft_p95_ms) : "—"}
          label="Phản hồi p95 · ngưỡng 3 s"
          alert={overBudget}
        />
        <Metric value={summary.total_tokens.toLocaleString("vi-VN")} label="Token đã dùng" />
      </div>

      <section className="panel">
        <p className="section-title">Phân bố yêu cầu theo ý định</p>
        {intents.length === 0 ? (
          <p className="empty__hint">Chưa có hội thoại nào được phân loại.</p>
        ) : (
          <div className="stack" style={{ gap: 10 }}>
            {intents.map(([intent, count]) => (
              <div key={intent} style={{ display: "grid", gap: 6 }}>
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    fontSize: 13,
                  }}
                >
                  <span>{INTENT_LABEL[intent] ?? intent}</span>
                  <span className="tnum" style={{ color: "var(--text-muted)" }}>
                    {count}
                  </span>
                </div>
                <div
                  style={{
                    height: 4,
                    borderRadius: 2,
                    background: "var(--surface-sunken)",
                    overflow: "hidden",
                  }}
                >
                  <div
                    style={{
                      width: `${Math.max(4, (count / busiest) * 100)}%`,
                      height: "100%",
                      background: "var(--accent)",
                    }}
                  />
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

function Metric({
  value,
  label,
  alert,
}: {
  value: number | string;
  label: string;
  alert?: boolean;
}) {
  return (
    <div className={`metric${alert ? " metric--alert" : ""}`}>
      <div className="metric-value">{value}</div>
      <div className="metric-label">{label}</div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
function QueueSkeleton() {
  return (
    <div className="panel" aria-busy="true" aria-label="Đang tải">
      {[0, 1, 2].map((row) => (
        <div key={row} style={{ marginBottom: 22 }}>
          <div className="skeleton skeleton--line" style={{ width: "34%", height: 16 }} />
          <div className="skeleton skeleton--line" style={{ width: "58%" }} />
          <div className="skeleton skeleton--line" style={{ width: "80%", marginBottom: 0 }} />
        </div>
      ))}
    </div>
  );
}

function TranscriptSkeleton() {
  return (
    <div aria-busy="true" aria-label="Đang tải hội thoại">
      <div className="skeleton skeleton--bubble" style={{ width: "72%", marginBottom: 14 }} />
      <div
        className="skeleton skeleton--bubble"
        style={{ width: "84%", marginLeft: "auto", marginBottom: 14 }}
      />
      <div className="skeleton skeleton--bubble" style={{ width: "66%" }} />
    </div>
  );
}

function summarise(args: Record<string, unknown> | null): string {
  if (!args) return "—";
  const parts = Object.entries(args)
    .filter(([key]) => key !== "conversation_id")
    .map(([key, value]) => `${key}=${String(value).slice(0, 46)}`);
  return parts.length ? parts.join("  ") : "—";
}
