export const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://127.0.0.1:8000";
export const WS_BASE = process.env.NEXT_PUBLIC_WS_BASE ?? "ws://127.0.0.1:8000";

export type Role = "customer" | "agent";

export type Session = {
  accessToken: string;
  role: Role;
  fullName: string;
  email: string;
};

export type PendingCase = {
  refund_code: string;
  amount: number;
  reason_code: string;
  reason_detail: string | null;
  fraud_score: number;
  created_at: string;
  conversation_id: string | null;
  resume_thread_id: string | null;
  customer_name: string;
  customer_email: string;
  ride_code: string | null;
};

export type DashboardSummary = {
  pending_hitl: number;
  open_tickets: number;
  total_messages: number;
  total_tokens: number;
  tool_calls: number;
  ttft_p95_ms: number | null;
  messages_by_intent: Record<string, number>;
};

export type QuotaAlert = {
  key: string;
  label: string;
  current: number;
  cap: number;
  unit: string;
  ratio_percent: number;
  level: "OK" | "WARN" | "DANGER";
};

export type DashboardStats = {
  tickets: { open: number; total: number };
  csat: { average: number | null; count: number };
  auto_resolve: { rate_percent: number | null; answered: number; escalated: number };
  tokens_today: number;
  by_intent: { intent: string; count: number }[];
  daily: { label: string; messages: number; tokens: number; refunded_vnd: number }[];
  alerts: QuotaAlert[];
};

export type TranscriptMessage = {
  role: string;
  content: string;
  intent: string | null;
  ttft_ms: number | null;
  created_at: string;
};

export type ToolCall = {
  tool_name: string;
  arguments: Record<string, unknown> | null;
  result: Record<string, unknown> | null;
  status: string;
  error_type: string | null;
  latency_ms: number | null;
  created_at: string;
};

export type Transcript = { messages: TranscriptMessage[]; tool_calls: ToolCall[] };

/** Thông báo lỗi giữ nguyên câu server trả về — nó đã viết cho người đọc. */
async function request<T>(path: string, init: RequestInit = {}, token?: string): Promise<T> {
  const headers: Record<string, string> = { ...(init.headers as Record<string, string>) };
  if (token) headers.Authorization = `Bearer ${token}`;
  if (init.body) headers["Content-Type"] = "application/json";

  const res = await fetch(`${API_BASE}${path}`, { ...init, headers });
  if (!res.ok) {
    const detail = await res.json().catch(() => null);
    throw new Error(detail?.detail ?? `Yêu cầu thất bại (HTTP ${res.status})`);
  }
  return res.json() as Promise<T>;
}

export async function login(email: string, password: string): Promise<Session> {
  const data = await request<{
    access_token: string;
    role: Role;
    full_name: string;
    email: string;
  }>("/api/auth/login", { method: "POST", body: JSON.stringify({ email, password }) });
  return {
    accessToken: data.access_token,
    role: data.role,
    fullName: data.full_name,
    email: data.email,
  };
}

export const fetchDashboard = (token: string) =>
  request<DashboardSummary>("/api/dashboard/summary", {}, token);

export const submitCsat = (
  token: string,
  threadId: string,
  score: number,
  comment: string | null,
) =>
  request<{ score: number; comment: string | null; created_at: string }>(
    `/api/chat/${encodeURIComponent(threadId)}/csat`,
    { method: "POST", body: JSON.stringify({ score, comment }) },
    token,
  );

export const fetchStats = (token: string) =>
  request<DashboardStats>("/api/dashboard/stats", {}, token);

export const fetchQueue = (token: string) =>
  request<{ pending: PendingCase[]; count: number }>("/api/hitl/queue", {}, token);

export const fetchTranscript = (token: string, conversationId: string) =>
  request<Transcript>(`/api/conversations/${conversationId}/transcript`, {}, token);

export const decideRefund = (
  token: string,
  refundCode: string,
  approved: boolean,
  reason: string | null,
) =>
  request<{ status: string; resumed: boolean; delivered_to_customer: number; message?: string }>(
    `/api/hitl/${encodeURIComponent(refundCode)}/decide`,
    { method: "POST", body: JSON.stringify({ approved, reason }) },
    token,
  );
