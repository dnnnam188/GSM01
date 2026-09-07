"use client";

import { useState, type FormEvent } from "react";
import { Shell } from "@/components/Shell";
import { login, type Session } from "@/lib/api";

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
            onChange={(event) => setEmail(event.target.value)}
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
            onChange={(event) => setPassword(event.target.value)}
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
      </form>
    </Shell>
  );
}
