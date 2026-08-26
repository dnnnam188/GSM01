"use client";

import { useState } from "react";
import { AgentDashboard } from "@/components/AgentDashboard";
import { CustomerChat } from "@/components/CustomerChat";
import { Login } from "@/components/Login";
import type { Session } from "@/lib/api";

export default function Home() {
  const [session, setSession] = useState<Session | null>(null);

  if (!session) return <Login onSignedIn={setSession} />;

  // Phân luồng theo vai trò chỉ là tiện lợi cho người dùng — quyền thật sự được
  // chặn ở server (`require_agent`), giao diện không phải nơi kiểm.
  return session.role === "agent" ? (
    <AgentDashboard session={session} onLogout={() => setSession(null)} />
  ) : (
    <CustomerChat session={session} onLogout={() => setSession(null)} />
  );
}
