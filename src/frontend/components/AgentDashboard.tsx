"use client";

import { useCallback, useEffect, useState } from "react";
import { Shell } from "@/components/Shell";
import {
  decideRefund,
  fetchDashboard,
  fetchStats,
  fetchQueue,
  fetchTranscript,
  type DashboardSummary,
  type DashboardStats,
  type QuotaAlert,
  type PendingCase,
  type Session,
  type Transcript,
} from "@/lib/api";
import { INTENT_LABEL, REASON_LABEL, money, ms, sinceNow, when } from "@/lib/format";

function RefreshIcon({ spinning }: { spinning: boolean }) {
  return (
    <svg
      className={spinning ? "refresh-icon refresh-icon--spin" : "refresh-icon"}
      viewBox="0 0 20 20"
      fill="none"
      aria-hidden="true"
    >
      <path d="M16 9a6 6 0 0 0-10.7-3.7L4 6.8M4 4v2.8h2.8M4 11a6 6 0 0 0 10.7 3.7l1.3-1.5M16 16v-2.8h-2.8" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function CheckIcon() {
  return (
    <svg viewBox="0 0 20 20" fill="none" aria-hidden="true">
      <path d="m4.5 10.2 3.6 3.6 7.4-7.6" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function EvidenceIcon() {
  return (
    <svg viewBox="0 0 20 20" fill="none" aria-hidden="true">
      <path d="M10 3.5a6.5 6.5 0 1 0 6.5 6.5A6.5 6.5 0 0 0 10 3.5Z" stroke="currentColor" strokeWidth="1.5" />
      <path d="M10 7v3.5l2.2 1.3" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

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
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [error, setError] = useState("");
  const [refreshing, setRefreshing] = useState(false);

  const reload = useCallback(async () => {
    setRefreshing(true);
    try {
      const [q, s, st] = await Promise.all([
        fetchQueue(session.accessToken),
        fetchDashboard(session.accessToken),
        fetchStats(session.accessToken),
      ]);
      setQueue(q.pending);
      setSummary(s);
      setStats(st);
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không tải được dữ liệu");
    } finally {
      setRefreshing(false);
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
      <div className="workspace-header">
        <div>
          <h1>Trung tâm điều phối CSKH</h1>
          <p className="lede">
            Tập trung vào những ca cần con người quyết định, với đầy đủ dữ liệu để xử lý tự tin.
          </p>
        </div>
        <div className="workspace-header__actions">
          <span className="system-status system-status--online">
            <span className="connection-state__dot" />
            Hệ thống ổn định
          </span>
          <button className="btn-quiet btn-refresh" onClick={() => void reload()} disabled={refreshing}>
            <RefreshIcon spinning={refreshing} />
            {refreshing ? "Đang cập nhật" : "Cập nhật"}
          </button>
        </div>
      </div>

      {error && (
        <div className="notice notice--danger notice--action" role="alert">
          <span>{error}</span>
          <button className="btn-text" onClick={() => void reload()}>Thử lại</button>
        </div>
      )}

      {tab === "queue" ? (
        <QueueView
          token={session.accessToken}
          cases={queue}
          onDecided={reload}
        />
      ) : (
        <StatsView summary={summary} stats={stats} />
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
      <div className="panel queue-empty-panel">
        <div className="empty">
          <div className="empty__illustration" aria-hidden="true"><CheckIcon /></div>
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
    <div className="split dashboard-split">
      <section className="panel panel--flush queue-panel">
        <div className="queue-panel__head">
          <div>
            <h2>Chờ quyết định</h2>
            <p className="queue-panel__sub">Các ca cần người duyệt trước khi hoàn tiền.</p>
          </div>
          <span className="queue-count">{cases.length} <small>ca</small></span>
        </div>
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

      <section className="panel evidence-panel">
        {openCase ? (
          <TranscriptView token={token} item={openCase} />
        ) : (
          <div className="empty">
            <div className="empty__illustration empty__illustration--soft" aria-hidden="true"><EvidenceIcon /></div>
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
      className={`case${selected ? " case--selected" : ""}`}
      style={{
        ["--i" as string]: index,
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

      <div className="case__context">
        <strong>{item.customer_name}</strong>
        <span>{item.ride_code ? `Chuyến ${item.ride_code}` : "Chưa có mã chuyến"}</span>
        <span>{sinceNow(item.created_at)}</span>
      </div>

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
        <div className="evidence-panel__title">
          <div>
            <h2>Hội thoại khách hàng</h2>
          </div>
          <span className="mono">{item.refund_code}</span>
        </div>
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
        <div className="trace__head">
          <h3 className="trace__title">Dấu vết xử lý</h3>
          <span className="badge">{data.tool_calls.length} bước</span>
        </div>
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
function StatsView({
  summary,
  stats,
}: {
  summary: DashboardSummary | null;
  stats: DashboardStats | null;
}) {
  if (!summary) return <QueueSkeleton />;

  const overBudget = summary.ttft_p95_ms !== null && summary.ttft_p95_ms >= 3000;
  const intents = Object.entries(summary.messages_by_intent).sort((a, b) => b[1] - a[1]);
  const busiest = intents[0]?.[1] ?? 1;
  // Chỉ nêu cảnh báo khi thật sự có chuyện. Một dải băng "mọi thứ đều ổn" nằm
  // thường trực trên đầu trang sẽ dạy người dùng bỏ qua đúng chỗ đó.
  const alerts = (stats?.alerts ?? []).filter((a) => a.level !== "OK");

  return (
    <div className="stack">
      <div className="section-lead">
      <div>
          <h2>Nhịp vận hành hôm nay</h2>
          <p className="section-lead__sub">Các chỉ số giúp ca trực biết nơi cần tập trung.</p>
        </div>
        <span className="section-lead__note">Dữ liệu cập nhật theo thời gian thực</span>
      </div>
      {alerts.map((a) => (
        <QuotaBanner key={a.key} alert={a} />
      ))}

      <div className="metrics">
        <Metric value={summary.pending_hitl} label="Chờ duyệt hoàn tiền" />
        <Metric
          value={stats ? `${stats.tickets.open}/${stats.tickets.total}` : "—"}
          label="Ticket đang mở / tổng"
        />
        <Metric
          value={
            stats?.auto_resolve.rate_percent === null ||
            stats?.auto_resolve.rate_percent === undefined
              ? "—"
              : `${stats.auto_resolve.rate_percent}%`
          }
          label="Tỷ lệ tự xử lý"
        />
        <Metric
          value={stats?.csat.average === null || stats?.csat.average === undefined
            ? "—"
            : stats.csat.average.toFixed(2)}
          label={`Điểm hài lòng · ${stats?.csat.count ?? 0} lượt`}
        />
        <Metric
          value={stats ? stats.tokens_today.toLocaleString("vi-VN") : "—"}
          label="Token hôm nay"
        />
        <Metric
          value={summary.ttft_p95_ms ? ms(summary.ttft_p95_ms) : "—"}
          label="Phản hồi p95 · ngưỡng 3 s"
          alert={overBudget}
        />
        <Metric value={summary.total_messages} label="Tin nhắn đã xử lý" />
        <Metric value={summary.tool_calls} label="Lượt gọi công cụ" />
      </div>

      {stats && <DailyChart daily={stats.daily} />}

      <section className="panel intent-panel">
        <div className="chart-head">
          <div>
            <h2>Phân bố yêu cầu theo ý định</h2>
          </div>
          <span className="chart-head__legend">Theo số lượt</span>
        </div>
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

/** Cảnh báo hạn mức trong ngày (F14). */
function QuotaBanner({ alert }: { alert: QuotaAlert }) {
  const vuot = alert.level === "DANGER";
  const so = (n: number) => n.toLocaleString("vi-VN");
  return (
    <div className={vuot ? "notice notice--danger notice--quota" : "notice notice--warn notice--quota"}>
      <span className="notice__icon" aria-hidden="true">!</span>
      <span>
        <strong>{vuot ? "Đã vượt hạn mức" : "Sắp chạm hạn mức"}</strong>
        <small>{alert.label}: <span className="tnum">{so(alert.current)} / {so(alert.cap)} {alert.unit}</span> ({alert.ratio_percent}%)</small>
      </span>
    </div>
  );
}

/** Biểu đồ 7 ngày. Cột dựng bằng CSS, không kéo thêm thư viện biểu đồ nào. */
function DailyChart({
  daily,
}: {
  daily: { label: string; messages: number; tokens: number; refunded_vnd: number }[];
}) {
  // Chia tỷ lệ theo giá trị lớn nhất, nhưng chặn dưới bằng 1 để ngày rỗng không
  // chia cho 0. Cột của ngày có dữ liệu luôn cao tối thiểu 2px, nếu không một
  // ngày ít việc sẽ trông y hệt ngày không có việc nào.
  const dinh = Math.max(1, ...daily.map((d) => d.messages));
  const tongHoan = daily.reduce((t, d) => t + d.refunded_vnd, 0);

  return (
    <section className="panel daily-panel">
      <div className="chart-head">
        <div>
          <h2>Hoạt động 7 ngày gần nhất</h2>
        </div>
        <span className="chart-head__legend"><i /> Tin nhắn</span>
      </div>
      <div
        className="daily-chart"
        style={{
          display: "grid",
          gridTemplateColumns: `repeat(${daily.length}, 1fr)`,
          alignItems: "end",
          gap: 8,
          height: 120,
        }}
      >
        {daily.map((d) => (
          <div key={d.label} style={{ display: "grid", gap: 6, justifyItems: "center" }}>
            <span className="tnum" style={{ fontSize: 12, color: "var(--text-muted)" }}>
              {d.messages || ""}
            </span>
            <div
              title={`${d.label}: ${d.messages} tin nhắn · ${d.tokens.toLocaleString("vi-VN")} token`}
              style={{
                width: "100%",
                height: d.messages ? Math.max(2, (d.messages / dinh) * 80) : 2,
                borderRadius: 3,
                background: d.messages ? "var(--accent)" : "var(--surface-sunken)",
              }}
            />
            <span style={{ fontSize: 12, color: "var(--text-muted)" }}>{d.label}</span>
          </div>
        ))}
      </div>
      <p className="empty__hint daily-total">
        Tổng hoàn tiền 7 ngày: {tongHoan.toLocaleString("vi-VN")} VNĐ
      </p>
    </section>
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
