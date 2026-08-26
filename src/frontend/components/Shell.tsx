"use client";

import type { Session } from "@/lib/api";

type Tab = { id: string; label: string; count?: number };

export function Shell({
  session,
  onLogout,
  tabs,
  activeTab,
  onTabChange,
  narrow,
  children,
}: {
  session?: Session;
  onLogout?: () => void;
  tabs?: Tab[];
  activeTab?: string;
  onTabChange?: (id: string) => void;
  narrow?: boolean;
  children: React.ReactNode;
}) {
  return (
    <div className={`shell${narrow ? " shell--narrow" : ""}`}>
      <header className="topbar">
        <p className="wordmark">
          GSM-01 <span>· Trợ lý CSKH Xanh SM</span>
        </p>

        {tabs && tabs.length > 0 && (
          <nav className="tabs" aria-label="Khu vực làm việc">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                className="tab"
                aria-current={tab.id === activeTab ? "page" : undefined}
                onClick={() => onTabChange?.(tab.id)}
              >
                {tab.label}
                {tab.count !== undefined && tab.count > 0 && (
                  <span className="tab__count">{tab.count}</span>
                )}
              </button>
            ))}
          </nav>
        )}

        <div className="topbar__spacer" />

        {session && (
          <div className="topbar__who">
            <span>
              {session.fullName}
              {" · "}
              {session.role === "agent" ? "Nhân viên CSKH" : "Khách hàng"}
            </span>
            <button className="btn-text" onClick={onLogout}>
              Đăng xuất
            </button>
          </div>
        )}
      </header>
      {children}
    </div>
  );
}
