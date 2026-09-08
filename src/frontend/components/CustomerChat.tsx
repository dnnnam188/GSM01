"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Shell } from "@/components/Shell";
import { createWsTicket, WS_BASE, submitCsat, type Session } from "@/lib/api";
import { INTENT_LABEL, ms } from "@/lib/format";

type ToolEvent = { name: string; ok: boolean; replayed: boolean; error: string | null };

type Turn = {
  who: "me" | "bot";
  text: string;
  intent?: string | null;
  ttftMs?: number | null;
  sources?: string[];
  tools?: ToolEvent[];
  awaitingHuman?: boolean;
  awaitingInfo?: boolean;
  degraded?: boolean;
  fromHuman?: boolean;
};

const SUGGESTIONS = [
  "Phí hủy chuyến với xe taxi là bao nhiêu?",
  "Chuyến XSM-DOUBLE-02 bị trừ tiền hai lần, hoàn lại cho tôi",
  "Tôi để quên ví trên xe",
];

function AssistantAvatar() {
  return (
    <span className="assistant-avatar" aria-hidden="true">
      <svg viewBox="0 0 32 32" fill="none">
        <path d="M7.5 19.5v-6A4.5 4.5 0 0 1 12 9h8a4.5 4.5 0 0 1 4.5 4.5v6" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
        <circle cx="11" cy="20" r="2" fill="currentColor" />
        <circle cx="21" cy="20" r="2" fill="currentColor" />
        <path d="M11 25h10" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
      </svg>
    </span>
  );
}

function SendIcon() {
  return (
    <svg viewBox="0 0 20 20" fill="none" aria-hidden="true">
      <path d="m3 3 14 7-14 7 2-6.5 7-1-7-1L3 3Z" fill="currentColor" />
    </svg>
  );
}

export function CustomerChat({
  session,
  onLogout,
}: {
  session: Session;
  onLogout: () => void;
}) {
  const [turns, setTurns] = useState<Turn[]>([]);
  const [draft, setDraft] = useState("");
  const [status, setStatus] = useState("Đang kết nối");
  const [connected, setConnected] = useState(false);
  const [waiting, setWaiting] = useState(false);
  const [threadId, setThreadId] = useState("");
  const [rated, setRated] = useState(false);
  const [csatHidden, setCsatHidden] = useState(false);
  const [connectAttempt, setConnectAttempt] = useState(0);
  const socket = useRef<WebSocket | null>(null);
  const threadIdRef = useRef("");
  const scroller = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const threadQuery = threadIdRef.current
      ? `?thread_id=${encodeURIComponent(threadIdRef.current)}`
      : "";
    const ws = new WebSocket(`${WS_BASE}/ws/chat${threadQuery}`);
    socket.current = ws;

    ws.onopen = async () => {
      try {
        const { ticket } = await createWsTicket(session.accessToken);
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: "auth", ticket }));
        }
      } catch {
        setStatus("Phiên đăng nhập đã hết hạn. Anh/chị đăng nhập lại giúp em ạ.");
        ws.close();
      }
    };

    ws.onclose = () => {
      setConnected(false);
      setStatus("Phiên hỗ trợ đã ngắt. Bạn có thể thử kết nối lại.");
    };
    ws.onerror = () => setStatus("Không thể kết nối tới máy chủ hỗ trợ.");

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);

      if (data.type === "ready") {
        setConnected(true);
        setStatus("Đang trực tuyến");
        setThreadId(data.thread_id ?? "");
        threadIdRef.current = data.thread_id ?? "";
        return;
      }

      if (data.type === "status") {
        setStatus(data.value);
        return;
      }

      if (data.type === "intent") {
        setTurns((prev) => [...prev, { who: "bot", text: "", intent: data.value, tools: [] }]);
        return;
      }

      if (data.type === "tool") {
        setTurns((prev) => patchLast(prev, (last) => ({
          ...last,
          tools: [
            ...(last.tools ?? []),
            { name: data.name, ok: data.ok, replayed: data.replayed, error: data.error },
          ],
        })));
        return;
      }

      if (data.type === "token") {
        setTurns((prev) => {
          const last = prev[prev.length - 1];
          if (!last || last.who !== "bot") return [...prev, { who: "bot", text: data.value }];
          return patchLast(prev, (turn) => ({ ...turn, text: turn.text + data.value }));
        });
        return;
      }

      if (data.type === "done") {
        setWaiting(false);
        setStatus("Đang trực tuyến");
        setTurns((prev) => patchLast(prev, (last) => ({
          ...last,
          ttftMs: data.ttft_ms ?? null,
          sources: data.sources ?? [],
          awaitingHuman: Boolean(data.awaiting_human),
          awaitingInfo: Boolean(data.awaiting_info),
          degraded: Boolean(data.degraded),
        })));
        return;
      }

      if (data.type === "hitl_result") {
        setTurns((prev) => [
          ...prev,
          { who: "bot", text: data.message, fromHuman: true, intent: "refund.request" },
        ]);
        setStatus("Đang trực tuyến");
        return;
      }

      if (data.type === "error") {
        setWaiting(false);
        setStatus(data.value);
      }
    };

    return () => ws.close();
  }, [session.accessToken, connectAttempt]);

  useEffect(() => {
    scroller.current?.scrollTo({ top: scroller.current.scrollHeight, behavior: "smooth" });
  }, [turns, waiting]);

  const send = useCallback(
    (text: string) => {
      const message = text.trim();
      if (!message || waiting || socket.current?.readyState !== WebSocket.OPEN) return;
      setTurns((prev) => [...prev, { who: "me", text: message }]);
      socket.current.send(JSON.stringify({ message }));
      setDraft("");
      setWaiting(true);
    },
    [waiting],
  );

  const awaitingHuman = turns.some((turn) => turn.awaitingHuman);
  const answered = turns.filter((turn) => turn.who === "bot").length;
  const askCsat =
    answered >= 2 && !waiting && !awaitingHuman && !csatHidden && Boolean(threadId);

  return (
    <Shell session={session} onLogout={onLogout}>
      <div className="page-heading page-heading--chat">
        <div>
          <p className="page-context">GREENSM CARE / CUSTOMER SUPPORT</p>
          <h1>Xin chào, {session.fullName}</h1>
          <p className="lede">Bạn cần hỗ trợ gì cho hành trình của mình hôm nay?</p>
        </div>
        <div className={`connection-state${connected ? " connection-state--online" : ""}`}>
          <span className="connection-state__dot" />
          <span>{connected ? "Đang trực tuyến" : "Đang kết nối"}</span>
        </div>
      </div>

      {awaitingHuman && (
        <div className="notice notice--human" role="status">
          <span className="notice__icon" aria-hidden="true">!</span>
          <span>
            <strong>Yêu cầu đang được nhân viên phụ trách xem xét.</strong>
            <small>Cứ để mở khung chat này — kết quả sẽ hiện ngay tại đây khi có.</small>
          </span>
        </div>
      )}

      <div className="chat-panel panel panel--flush">
        <div className="chat-panel__top">
          <div className="chat-panel__assistant">
            <AssistantAvatar />
            <span>
              <strong>Trợ lý GreenSM</strong>
              <small>Tra cứu chuyến đi · chính sách · hỗ trợ khiếu nại</small>
            </span>
          </div>
          <span className="chat-panel__secure">
            <span className="secure-dot" />
            Phiên riêng tư
          </span>
        </div>

        <div className="thread" ref={scroller}>
          {turns.length === 0 && !waiting && (
            <div className="welcome-state">
              <div className="welcome-state__mark"><AssistantAvatar /></div>
              <h2>Bạn cần hỗ trợ gì ạ?</h2>
              <p>
                Tôi có thể tra cước, tìm chuyến đã đi, hỗ trợ đặt hoặc hủy chuyến,
                tiếp nhận thất lạc đồ và yêu cầu hoàn tiền.
              </p>
              <div className="suggestion-list" aria-label="Gợi ý câu hỏi">
                {SUGGESTIONS.map((text) => (
                  <button
                    key={text}
                    className="suggestion"
                    onClick={() => send(text)}
                    disabled={!connected}
                  >
                    <span>{text}</span>
                    <span aria-hidden="true">↗</span>
                  </button>
                ))}
              </div>
            </div>
          )}

          {turns.map((turn, index) => (
            <div key={index} className={`turn turn--${turn.who}`}>
              <div className="bubble">{turn.text || "…"}</div>
              {turn.who === "bot" && <TurnMeta turn={turn} />}
            </div>
          ))}

          {waiting && <PendingBubble />}

          {askCsat && (
            <CsatPrompt
              rated={rated}
              onRate={async (score) => {
                try {
                  await submitCsat(session.accessToken, threadId, score, null);
                  setRated(true);
                  setTimeout(() => setCsatHidden(true), 2500);
                } catch {
                  setStatus("Chưa gửi được đánh giá, bạn thử lại giúp em ạ");
                }
              }}
              onDismiss={() => setCsatHidden(true)}
            />
          )}
        </div>

        <div className="composer-area">
          <form
            className="composer"
            onSubmit={(event) => {
              event.preventDefault();
              send(draft);
            }}
          >
            <input
              value={draft}
              onChange={(event) => setDraft(event.target.value)}
              placeholder="Viết tin nhắn cho GreenSM…"
              aria-label="Tin nhắn gửi trợ lý"
              disabled={!connected || waiting}
            />
            <button className="btn-primary composer__send" type="submit" disabled={waiting || !draft.trim()}>
              <span>Gửi</span>
              <SendIcon />
            </button>
          </form>
          <p className={`status-line${connected ? " status-line--ok" : " status-line--muted"}`}>
            <span className={`status-dot${waiting ? " status-dot--pulse" : ""}`} aria-hidden="true" />
            <span>{status}</span>
            {!connected && !waiting && (
              <button
                className="btn-text status-line__retry"
                type="button"
                onClick={() => setConnectAttempt((attempt) => attempt + 1)}
              >
                Thử kết nối lại
              </button>
            )}
          </p>
        </div>
      </div>
    </Shell>
  );
}

/** Hỏi mức hài lòng 1–5 cuối phiên (F16). */
function CsatPrompt({
  rated,
  onRate,
  onDismiss,
}: {
  rated: boolean;
  onRate: (score: number) => void;
  onDismiss: () => void;
}) {
  if (rated) {
    return <p className="csat-thanks">Cảm ơn anh/chị đã đánh giá phiên hỗ trợ.</p>;
  }
  return (
    <div className="csat-card">
      <div>
        <strong>Phiên hỗ trợ vừa rồi thế nào?</strong>
        <span>Chấm điểm để GreenSM phục vụ tốt hơn.</span>
      </div>
      <div className="csat-actions">
        <div className="csat-scale" aria-label="Đánh giá từ 1 đến 5">
          {[1, 2, 3, 4, 5].map((score) => (
            <button key={score} className="csat-score" onClick={() => onRate(score)} aria-label={`Chấm ${score} trên 5`}>
              {score}
            </button>
          ))}
        </div>
        <button className="btn-text" onClick={onDismiss}>Bỏ qua</button>
      </div>
    </div>
  );
}

function TurnMeta({ turn }: { turn: Turn }) {
  const hasMeta =
    turn.intent || turn.ttftMs || turn.sources?.length || turn.tools?.length || turn.fromHuman;
  if (!hasMeta) return null;

  return (
    <div className="turn__meta">
      {turn.fromHuman && <span className="badge badge--accent">Nhân viên đã duyệt</span>}
      {turn.intent && !turn.fromHuman && (
        <span className="badge">{INTENT_LABEL[turn.intent] ?? turn.intent}</span>
      )}
      {turn.awaitingHuman && <span className="badge badge--warn">Chờ nhân viên duyệt</span>}
      {turn.awaitingInfo && <span className="badge badge--info">Cần thêm thông tin</span>}
      {turn.degraded && <span className="badge badge--danger">Trả lời hạn chế</span>}
      {turn.tools?.map((tool, index) => (
        <span key={index} className={`badge${tool.ok ? "" : " badge--danger"}`}>
          {tool.name}
          {tool.replayed ? " · đã làm trước đó" : ""}
        </span>
      ))}
      {turn.ttftMs ? <span className="tnum">{ms(turn.ttftMs)}</span> : null}
      {turn.sources?.length ? <span>nguồn: {turn.sources.join(", ")}</span> : null}
    </div>
  );
}

function PendingBubble() {
  return (
    <div className="turn turn--bot" aria-live="polite" aria-label="Đang soạn câu trả lời">
      <div className="bubble bubble--pending">
        <span className="thinking-dot" /><span className="thinking-dot" /><span className="thinking-dot" />
      </div>
      <div className="turn__meta"><span>GreenSM đang kiểm tra thông tin…</span></div>
    </div>
  );
}

function patchLast(turns: Turn[], patch: (turn: Turn) => Turn): Turn[] {
  if (turns.length === 0) return turns;
  const next = [...turns];
  next[next.length - 1] = patch(next[next.length - 1]);
  return next;
}
