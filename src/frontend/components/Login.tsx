"use client";

import { useState, type FormEvent } from "react";
import { Shell } from "@/components/Shell";
import { login, type Session } from "@/lib/api";

function ArrowIcon() {
  return (
    <svg viewBox="0 0 20 20" fill="none" aria-hidden="true">
      <path d="M4 10h11M10.5 5.5 15 10l-4.5 4.5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function ShieldIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path d="M12 3.5 19 6v5.4c0 4.1-2.7 7.6-7 9.1-4.3-1.5-7-5-7-9.1V6l7-2.5Z" stroke="currentColor" strokeWidth="1.7" strokeLinejoin="round" />
      <path d="m9 12 2 2 4-4" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function SparkIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path d="m12 3 1.3 5.7L19 10l-5.7 1.3L12 17l-1.3-5.7L5 10l5.7-1.3L12 3Z" fill="currentColor" />
      <path d="m19 15 .6 2.4L22 18l-2.4.6L19 21l-.6-2.4L16 18l2.4-.6L19 15Z" fill="currentColor" opacity=".7" />
    </svg>
  );
}

export function Login({ onSignedIn }: { onSignedIn: (session: Session) => void }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      onSignedIn(await login(email, password));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không đăng nhập được. Bạn thử lại nhé.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Shell narrow>
      <div className="login-page">
        <section className="login-intro" aria-labelledby="login-title">
          <div className="login-intro__signal">
            <span className="signal-dot" />
            <span>GreenSM care workspace</span>
          </div>
          <h1 id="login-title">Mỗi hành trình đều xứng đáng được chăm sóc tử tế.</h1>
          <p>
            GSM-01 giúp khách hàng nhận hỗ trợ rõ ràng hơn và giúp đội CSKH xử lý đúng việc,
            đúng người, đúng thời điểm.
          </p>

          <div className="login-intro__proof" aria-label="Điểm nổi bật của hệ thống">
            <div className="proof-item">
              <span className="proof-icon"><SparkIcon /></span>
              <span><strong>Hỗ trợ tức thì</strong><small>Tra cứu chuyến, cước phí và chính sách trong một luồng chat.</small></span>
            </div>
            <div className="proof-item">
              <span className="proof-icon"><ShieldIcon /></span>
              <span><strong>Quyết định có kiểm soát</strong><small>Những yêu cầu rủi ro luôn được chuyển tới nhân viên phụ trách.</small></span>
            </div>
          </div>
        </section>

        <section className="login-card" aria-label="Biểu mẫu đăng nhập">
          <div className="login-card__header">
            <span className="login-card__label">GSM-01 / ACCESS</span>
            <h2>Chào mừng trở lại</h2>
            <p>Đăng nhập để tiếp tục phiên hỗ trợ của bạn.</p>
          </div>

          <form onSubmit={submit}>
            <div className="field">
              <label htmlFor="email">Email</label>
              <input
                id="email"
                type="email"
                value={email}
                autoComplete="username"
                autoFocus
                placeholder="you@greensm.vn"
                onChange={(event) => setEmail(event.target.value)}
                required
              />
            </div>

            <div className="field">
              <div className="field__label-row">
                <label htmlFor="password">Mật khẩu</label>
                <span className="field__hint">Bảo mật</span>
              </div>
              <input
                id="password"
                type="password"
                value={password}
                autoComplete="current-password"
                placeholder="Nhập mật khẩu của bạn"
                onChange={(event) => setPassword(event.target.value)}
                required
              />
            </div>

            <button className="btn-primary btn-submit" type="submit" disabled={busy}>
              <span>{busy ? "Đang xác thực…" : "Đăng nhập workspace"}</span>
              {!busy && <ArrowIcon />}
            </button>

            {error && (
              <div className="form-error" role="alert">
                <span className="form-error__dot" aria-hidden="true" />
                <span>{error}</span>
              </div>
            )}
          </form>

          <p className="login-card__footer">
            <ShieldIcon />
            Phiên làm việc được bảo vệ bằng xác thực JWT và phân quyền theo vai trò.
          </p>
        </section>
      </div>
    </Shell>
  );
}
