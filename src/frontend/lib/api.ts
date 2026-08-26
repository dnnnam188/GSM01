export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE ?? "http://127.0.0.1:8000";
export const WS_BASE =
  process.env.NEXT_PUBLIC_WS_BASE ?? "ws://127.0.0.1:8000";

export type Session = {
  accessToken: string;
  role: "customer" | "agent";
  fullName: string;
  email: string;
};

export async function login(email: string, password: string): Promise<Session> {
  const res = await fetch(`${API_BASE}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({ detail: "Đăng nhập thất bại" }));
    throw new Error(detail.detail ?? "Đăng nhập thất bại");
  }
  const data = await res.json();
  return {
    accessToken: data.access_token,
    role: data.role,
    fullName: data.full_name,
    email: data.email,
  };
}

export async function fetchDashboard(token: string) {
  const res = await fetch(`${API_BASE}/api/dashboard/summary`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error(`Không tải được dashboard (HTTP ${res.status})`);
  return res.json();
}
