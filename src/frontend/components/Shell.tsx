"use client";

import type { Session } from "@/lib/api";

type Tab = { id: string; label: string; count?: number };

function BrandMark() {
  return (
    <span className="brand-mark" aria-hidden="true">
      <svg viewBox="0 0 40 40" fill="none">
        <path
          d="M9.5 24.5v-8.2A6.3 6.3 0 0 1 15.8 10h8.4a6.3 6.3 0 0 1 6.3 6.3v8.2"
          stroke="currentColor"
          strokeWidth="2.5"
          strokeLinecap="round"
        />
        <circle cx="14" cy="25.5" r="3" fill="currentColor" />
        <circle cx="26" cy="25.5" r="3" fill="currentColor" />
        <path d="M13 31h14" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" />
      </svg>
    </span>
  );
}

function LogoutIcon() {
  return (
    <svg viewBox="0 0 20 20" fill="none" aria-hidden="true">
      <path d="M8 3H4.5A1.5 1.5 0 0 0 3 4.5v11A1.5 1.5 0 0 0 4.5 17H8" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
      <path d="m11 6.5 3.5 3.5-3.5 3.5M14 10H7" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

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
  const initials = session?.fullName
    ?.split(" ")
    .filter(Boolean)
    .slice(-2)
    .map((part) => part[0])
    .join("")
    .toUpperCase();

  return (
    <div className={`shell${narrow ? " shell--narrow" : ""}`}>
      <header className="topbar">
        <div className="brand" aria-label="GreenSM Care, GSM-01">
          <BrandMark />
          <span className="brand-copy">
            <strong>GreenSM</strong>
            <span>Customer care · GSM-01</span>
          </span>
        </div>

        {tabs && tabs.length > 0 && (
          <nav className="tabs" aria-label="Khu vực làm việc">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                className="tab"
                aria-current={tab.id === activeTab ? "page" : undefined}
                onClick={() => onTabChange?.(tab.id)}
              >
                <span>{tab.label}</span>
                {tab.count !== undefined && (
                  <span className={`tab__count${tab.count > 0 ? " tab__count--active" : ""}`}>
                    {tab.count}
                  </span>
                )}
              </button>
            ))}
          </nav>
        )}

        <div className="topbar__spacer" />

        {session ? (
          <div className="topbar__who">
            <span className="user-avatar" aria-hidden="true">{initials || "G"}</span>
            <span className="topbar__identity">
              <strong>{session.fullName}</strong>
              <span>{session.role === "agent" ? "Nhân viên CSKH" : "Khách hàng"}</span>
            </span>
            <button className="btn-text btn-logout" onClick={onLogout}>
              <LogoutIcon />
              <span>Đăng xuất</span>
            </button>
          </div>
        ) : (
          <span className="topbar__mode">GSM-01 / SUPPORT OPS</span>
        )}
      </header>
      <main className="shell__content">{children}</main>
    </div>
  );
}
