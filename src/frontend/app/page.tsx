"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { WS_BASE, fetchDashboard, login, type Session } from "@/lib/api";

type Turn = {
  role: "user" | "bot";
  text: string;
  intent?: string;
  confidence?: number;
  ttftMs?: number | null;
  sources?: string[];
  provider?: string;
  degraded?: boolean;
};

export default function Home() {
  const [session, setSession] = useState<Session | null>(null);
  if (!session) return <Login onDone={setSession} />;
  return session.role === "agent" ? (
    <AgentDashboard session={session} onLogout={() => setSession(null)} />
  ) : (
    <CustomerChat session={session} onLogout={() => setSession(null)} />
  );
}

function Shell({ title, session, onLogout, children }: {
  title: string;
  session?: Session;
  onLogout?: () => void;
  children: React.ReactNode;
}) {
  return (
    <div className="shell">
      <div className="header">
        <h1>{title}</h1>
        {session && (
          <span className="who">
            {session.fullName} · {session.role}{" "}
            <button className="ghost" style={{ width: "auto", padding: "4px 10px", marginLeft: 8 }}
                    onClick={onLogout}>
              Đăng xuất
            </button>
          </span>
        )}
      </div>
      {children}
    </div>
  );
}

function Login({ onDone }: { onDone: (s: Session) => void }) {
  const [email, setEmail] = useState("demo.customer@gsm.vn");
  const [password, setPassword] = useState("Demo@123");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      onDone(await login(email, password));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Đăng nhập thất bại");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Shell title="GSM-01 · Trợ lý CSKH Xanh SM">
      <form className="panel" onSubmit={submit}>
        <div className="field">
          <label htmlFor="email">Email</label>
          <input id="email" type="email" value={email} autoComplete="username"
                 onChange={(e) => setEmail(e.target.value)} required />
        </div>
        <div className="field">
          <label htmlFor="password">Mật khẩu</label>
          <input id="password" type="password" value={password} autoComplete="current-password"
                 onChange={(e) => setPassword(e.target.value)} required />
        </div>
        <button type="submit" disabled={busy}>
          {busy ? "Đang đăng nhập…" : "Đăng nhập"}
        </button>
        {error && <div className="error">{error}</div>}
        <div className="hint">
          Tài khoản demo — mật khẩu chung <code>Demo@123</code>
          <div style={{ marginTop: 6 }}>
            <button className="ghost" style={{ width: "auto", padding: "4px 10px", marginRight: 8 }}
                    type="button" onClick={() => setEmail("demo.customer@gsm.vn")}>
              Khách hàng
            </button>
            <button className="ghost" style={{ width: "auto", padding: "4px 10px" }}
                    type="button" onClick={() => setEmail("agent01@gsm.vn")}>
              Nhân viên CSKH
            </button>
          </div>
        </div>
      </form>
    </Shell>
  );
}

function CustomerChat({ session, onLogout }: { session: Session; onLogout: () => void }) {
  const [turns, setTurns] = useState<Turn[]>([]);
  const [draft, setDraft] = useState("");
  const [status, setStatus] = useState("Đang kết nối…");
  const [waiting, setWaiting] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const scrollRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const ws = new WebSocket(`${WS_BASE}/ws/chat?token=${encodeURIComponent(session.accessToken)}`);
    wsRef.current = ws;

    ws.onopen = () => setStatus("Đã kết nối");
    ws.onclose = () => setStatus("Mất kết nối — tải lại trang để thử lại");
    ws.onerror = () => setStatus("Lỗi kết nối tới máy chủ");
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === "ready") {
        setStatus("Sẵn sàng");
      } else if (data.type === "status") {
        setStatus(data.value);
      } else if (data.type === "intent") {
        setTurns((prev) => [...prev, {
          role: "bot", text: "", intent: data.value, confidence: data.confidence,
        }]);
      } else if (data.type === "token") {
        setTurns((prev) => {
          const next = [...prev];
          const last = next[next.length - 1];
          // Lỗi ở tầng router không sinh sự kiện `intent`, nên có thể chưa có bong bóng nào
          if (!last || last.role !== "bot") {
            next.push({ role: "bot", text: data.value });
          } else {
            next[next.length - 1] = { ...last, text: last.text + data.value };
          }
          return next;
        });
      } else if (data.type === "done") {
        setWaiting(false);
        setStatus("Sẵn sàng");
        setTurns((prev) => {
          const next = [...prev];
          const last = next[next.length - 1];
          if (last?.role === "bot") {
            next[next.length - 1] = {
              ...last, ttftMs: data.ttft_ms, sources: data.sources,
              provider: data.provider, degraded: data.degraded,
            };
          }
          return next;
        });
      } else if (data.type === "error") {
        setWaiting(false);
        setStatus(data.value);
      }
    };
    return () => ws.close();
  }, [session.accessToken]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [turns]);

  const send = useCallback((e: React.FormEvent) => {
    e.preventDefault();
    const text = draft.trim();
    if (!text || waiting || wsRef.current?.readyState !== WebSocket.OPEN) return;
    setTurns((prev) => [...prev, { role: "user", text }]);
    wsRef.current.send(JSON.stringify({ message: text }));
    setDraft("");
    setWaiting(true);
  }, [draft, waiting]);

  return (
    <Shell title="Trợ lý CSKH Xanh SM" session={session} onLogout={onLogout}>
      <div className="note">
        Bản vertical slice (T-009): agent tra cứu được chính sách và biểu phí. Các thao tác
        đặt / huỷ / hoàn tiền <strong>chưa được nối tool</strong> — agent sẽ ghi nhận và nói rõ
        là đang chuyển tiếp, chứ không xác nhận đã thực hiện.
      </div>
      <div className="panel">
        <div className="chat" ref={scrollRef}>
          {turns.length === 0 && (
            <div className="status">
              Thử hỏi: “Phí hủy chuyến với xe taxi là bao nhiêu?” rồi hỏi tiếp “Thế còn xe máy?”
            </div>
          )}
          {turns.map((turn, i) => (
            <div key={i}>
              <div className={`msg ${turn.role}`}>{turn.text || "…"}</div>
              {turn.role === "bot" && (turn.intent || turn.ttftMs) && (
                <div className="meta">
                  {turn.intent && <span className="badge">{turn.intent}</span>}
                  {turn.confidence !== undefined && <span>conf {turn.confidence}</span>}
                  {turn.ttftMs != null && <span>TTFT {turn.ttftMs} ms</span>}
                  {turn.provider && <span>{turn.provider}</span>}
                  {turn.sources?.length ? <span>nguồn: {turn.sources.join(", ")}</span> : null}
                  {turn.degraded && <span>⚠️ trả lời hạn chế</span>}
                </div>
              )}
            </div>
          ))}
        </div>
        <form className="composer" onSubmit={send}>
          <input value={draft} onChange={(e) => setDraft(e.target.value)}
                 placeholder="Nhập tin nhắn…" disabled={waiting} aria-label="Tin nhắn" />
          <button type="submit" disabled={waiting || !draft.trim()}>
            {waiting ? "Đang gửi…" : "Gửi"}
          </button>
        </form>
        <div className="status" style={{ marginTop: 8 }}>{status}</div>
      </div>
    </Shell>
  );
}

function AgentDashboard({ session, onLogout }: { session: Session; onLogout: () => void }) {
  const [data, setData] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    fetchDashboard(session.accessToken)
      .then(setData)
      .catch((err) => setError(err instanceof Error ? err.message : "Lỗi tải dữ liệu"));
  }, [session.accessToken]);

  const byIntent = (data?.messages_by_intent ?? {}) as Record<string, number>;

  return (
    <Shell title="Dashboard CSKH" session={session} onLogout={onLogout}>
      <div className="note">
        Bản rút gọn của T-009. Hàng đợi duyệt hoàn tiền và tool trace đầy đủ làm ở T-005/T-011.
      </div>
      {error && <div className="panel"><div className="error">{error}</div></div>}
      {data && (
        <>
          <div className="panel" style={{ marginBottom: 16 }}>
            <div className="stats">
              <div className="stat">
                <div className="n">{String(data.pending_hitl)}</div>
                <div className="l">Chờ duyệt hoàn tiền</div>
              </div>
              <div className="stat">
                <div className="n">{String(data.open_tickets)}</div>
                <div className="l">Ticket đang mở</div>
              </div>
              <div className="stat">
                <div className="n">{String(data.total_messages)}</div>
                <div className="l">Tin nhắn đã xử lý</div>
              </div>
              <div className="stat">
                <div className="n">{String(data.tool_calls)}</div>
                <div className="l">Lượt gọi tool</div>
              </div>
              <div className="stat">
                <div className="n">{data.ttft_p95_ms ? `${data.ttft_p95_ms} ms` : "—"}</div>
                <div className="l">TTFT p95 (ngưỡng 3000 ms)</div>
              </div>
              <div className="stat">
                <div className="n">{Number(data.total_tokens).toLocaleString("vi-VN")}</div>
                <div className="l">Tổng token đã dùng</div>
              </div>
            </div>
          </div>
          <div className="panel">
            <strong style={{ fontSize: 14 }}>Phân bố ý định</strong>
            {Object.keys(byIntent).length === 0 ? (
              <div className="status" style={{ marginTop: 8 }}>Chưa có dữ liệu.</div>
            ) : (
              <div style={{ marginTop: 10 }}>
                {Object.entries(byIntent).map(([intent, count]) => (
                  <div key={intent} className="meta" style={{ justifyContent: "space-between" }}>
                    <span className="badge">{intent}</span>
                    <span>{count}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </>
      )}
    </Shell>
  );
}
