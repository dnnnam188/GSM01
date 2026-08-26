"use client";

import { useState } from "react";
import { Shell } from "@/components/Shell";
import { login, type Session } from "@/lib/api";

const DEMO_ACCOUNTS = [
  { email: "demo.customer@gsm.vn", label: "Khách hàng", note: "Nguyễn Minh Khang" },
  { email: "agent01@gsm.vn", label: "Nhân viên CSKH", note: "Trần Thị Lan" },
];

export function Login({ onSignedIn }: { onSignedIn: (session: Session) => void }) {
  const [email, setEmail] = useState(DEMO_ACCOUNTS[0].email);
  const [password, setPassword] = useState("Demo@123");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      onSignedIn(await login(email, password));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không đăng nhập được");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Shell narrow>
      <h1>Đăng nhập</h1>
      <p className="lede">
        Hệ thống có hai vai trò tách biệt. Khách hàng dùng khung chat; nhân viên CSKH
        dùng bảng điều hành để duyệt các yêu cầu vượt hạn mức tự động.
      </p>

      <form className="panel" onSubmit={submit}>
        <div className="field">
          <label htmlFor="email">Email</label>
          <input
            id="email"
            type="email"
            value={email}
            autoComplete="username"
            onChange={(e) => setEmail(e.target.value)}
            required
          />
        </div>

        <div className="field">
          <label htmlFor="password">Mật khẩu</label>
          <input
            id="password"
            type="password"
            value={password}
            autoComplete="current-password"
            onChange={(e) => setPassword(e.target.value)}
            required
          />
        </div>

        <button className="btn-primary" type="submit" disabled={busy}>
          {busy ? "Đang kiểm tra…" : "Đăng nhập"}
        </button>

        {error && (
          <p className="error-text" role="alert">
            {error}
          </p>
        )}

        <div style={{ marginTop: 22, paddingTop: 16, borderTop: "1px solid var(--border)" }}>
          <p className="section-title" style={{ marginBottom: 10 }}>
            Tài khoản dùng thử
          </p>
          <div className="row">
            {DEMO_ACCOUNTS.map((account) => (
              <button
                key={account.email}
                type="button"
                className="btn-quiet"
                onClick={() => setEmail(account.email)}
                style={{ textAlign: "left", flex: "1 1 200px" }}
              >
                <span style={{ display: "block", fontWeight: 600, color: "var(--text)" }}>
                  {account.label}
                </span>
                <span className="mono" style={{ fontSize: 11.5 }}>
                  {account.email}
                </span>
              </button>
            ))}
          </div>
          <p style={{ fontSize: 12.5, color: "var(--text-faint)", marginTop: 10, marginBottom: 0 }}>
            Mật khẩu chung: <code className="mono">Demo@123</code>
          </p>
        </div>
      </form>
    </Shell>
  );
}
