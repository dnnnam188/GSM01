"use client";

import { useState, type FormEvent } from "react";
import { BrandLogo, Shell } from "@/components/Shell";
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
          <div className="login-visual">
            <div className="login-visual__content">
              <div className="login-visual__brand">
                <BrandLogo />
                <span className="login-visual__code">GSM-01 / customer care</span>
              </div>
              <div className="login-visual__copy">
                <h1 id="login-title">Chăm sóc từng hành trình, rõ ràng từ bước đầu.</h1>
                <p>
                  Không gian hỗ trợ dành cho khách hàng và đội CSKH GreenSM — nơi mỗi quyết định
                  đều có dữ liệu đứng phía sau.
                </p>
                <div className="login-visual__meta" aria-label="Điểm nổi bật của hệ thống">
                  <span>
                    <strong>Hỗ trợ đúng việc</strong>
                    <small>Tra cứu chuyến, cước phí và chính sách trong một luồng.</small>
                  </span>
                  <span>
                    <strong>Quyết định có kiểm soát</strong>
                    <small>Ca rủi ro luôn được chuyển tới nhân viên phụ trách.</small>
                  </span>
                </div>
              </div>
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
