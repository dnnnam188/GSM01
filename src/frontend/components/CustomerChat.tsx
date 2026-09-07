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
      setStatus("Mất kết nối. Tải lại trang để tiếp tục.");
    };
    ws.onerror = () => setStatus("Không kết nối được tới máy chủ");

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);

      if (data.type === "ready") {
        setConnected(true);
        setStatus("Sẵn sàng");
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
          // Lỗi ở tầng router không sinh sự kiện `intent`, nên có thể chưa có bong bóng
          if (!last || last.who !== "bot") return [...prev, { who: "bot", text: data.value }];
          return patchLast(prev, (turn) => ({ ...turn, text: turn.text + data.value }));
        });
        return;
      }

      if (data.type === "done") {
        setWaiting(false);
        setStatus("Sẵn sàng");
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

      // Nhân viên CSKH vừa quyết định — kết quả đẩy thẳng vào phiên đang mở
      if (data.type === "hitl_result") {
        setTurns((prev) => [
          ...prev,
          { who: "bot", text: data.message, fromHuman: true, intent: "refund.request" },
        ]);
        setStatus("Sẵn sàng");
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
  // Hỏi điểm khi phiên đã thực sự diễn ra (từ 2 lượt trả lời trở lên) và lượt
  // cuối đã xong. Hỏi ngay sau câu đầu tiên là hỏi giữa chừng, không phải cuối
  // phiên — và đang chờ CSKH duyệt thì phiên chưa kết thúc để mà chấm.
  const answered = turns.filter((turn) => turn.who === "bot").length;
  const askCsat =
    answered >= 2 && !waiting && !awaitingHuman && !csatHidden && Boolean(threadId);

  return (
    <Shell session={session} onLogout={onLogout}>
      {awaitingHuman && (
        <p className="notice notice--warn">
          Yêu cầu của bạn đang chờ nhân viên phụ trách xem xét. Cứ để mở khung chat này —
          kết quả sẽ hiện ngay tại đây khi có.
        </p>
      )}

      <div className="panel">
        <div className="thread" ref={scroller}>
          {turns.length === 0 && !waiting && (
            <div className="empty">
              <p className="empty__title">Bạn cần hỗ trợ gì ạ?</p>
              <p className="empty__hint">
                Hỏi về cước phí, tra cứu chuyến đã đi, báo thất lạc đồ, hoặc yêu cầu
                hoàn tiền. Thử một trong các câu dưới đây.
              </p>
              <div className="row" style={{ justifyContent: "center", marginTop: 18 }}>
                {SUGGESTIONS.map((text) => (
                  <button
                    key={text}
                    className="btn-quiet"
                    onClick={() => send(text)}
                    disabled={!connected}
                  >
                    {text}
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
                  // Để lời cảm ơn nán lại một nhịp rồi mới thu gọn, chứ biến mất
                  // ngay thì khách không kịp thấy điểm đã được ghi nhận.
                  setTimeout(() => setCsatHidden(true), 2500);
                } catch {
                  setStatus("Chưa gửi được đánh giá, bạn thử lại giúp em ạ");
                }
              }}
              onDismiss={() => setCsatHidden(true)}
            />
          )}
        </div>

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
            placeholder="Nhập tin nhắn…"
            aria-label="Tin nhắn gửi trợ lý"
            disabled={!connected || waiting}
          />
          <button className="btn-primary" type="submit" disabled={waiting || !draft.trim()}>
            Gửi
          </button>
        </form>

        <p className="status-line">
          {waiting && <span className="pulse" aria-hidden />}
          {status}
          {!connected && !waiting && (
            <button
              className="btn-text"
              type="button"
              onClick={() => setConnectAttempt((attempt) => attempt + 1)}
            >
              Thử kết nối lại
            </button>
          )}
        </p>
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
    return (
      <p className="status-line" style={{ justifyContent: "center" }}>
        Cảm ơn anh/chị đã đánh giá.
      </p>
    );
  }
  return (
    <div className="panel" style={{ padding: 16, textAlign: "center" }}>
      <p className="empty__hint" style={{ marginBottom: 12 }}>
        Em hỗ trợ anh/chị vừa rồi có ổn không ạ? (1 = rất tệ, 5 = rất tốt)
      </p>
      <div className="row" style={{ justifyContent: "center", gap: 8 }}>
        {[1, 2, 3, 4, 5].map((score) => (
          <button
            key={score}
            className="btn-quiet tnum"
            style={{ minWidth: 44 }}
            onClick={() => onRate(score)}
            aria-label={`Chấm ${score} trên 5`}
          >
            {score}
          </button>
        ))}
      </div>
      <button
        className="btn-quiet"
        style={{ marginTop: 10, fontSize: 13 }}
        onClick={onDismiss}
      >
        Bỏ qua
      </button>
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

/** Skeleton giữ đúng hình dạng bong bóng sắp hiện, thay vì vòng xoay chung chung. */
function PendingBubble() {
  return (
    <div className="turn turn--bot" aria-live="polite" aria-label="Đang soạn câu trả lời">
      <div className="skeleton skeleton--bubble" />
      <div className="turn__meta" style={{ width: 140 }}>
        <div className="skeleton skeleton--line" style={{ width: "100%", marginBottom: 0 }} />
      </div>
    </div>
  );
}

function patchLast(turns: Turn[], patch: (turn: Turn) => Turn): Turn[] {
  if (turns.length === 0) return turns;
  const next = [...turns];
  next[next.length - 1] = patch(next[next.length - 1]);
  return next;
}
