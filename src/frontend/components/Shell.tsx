"use client";

import type { Session } from "@/lib/api";

type Tab = { id: string; label: string; count?: number };

export function BrandLogo({ className = "" }: { className?: string }) {
  return (
    <svg
      className={`brand-logo ${className}`}
      viewBox="0 0 110 32"
      role="img"
      aria-label="Green SM"
    >
      <path d="M88.7 25.2c1 .9 2.9 1.5 4.1 1.5s1-.3 1-.6c0-.4-.5-.5-1.5-.8-2.4-.6-4.5-1.5-4.5-3.8s1.6-3.5 4.5-3.5 3.2.4 4.8 1.5L95.5 22c-1.3-.8-2.2-1.1-3.3-1.1s-1 .2-1 .6.4.7 1.6.9c2.6.6 4.4 1.6 4.4 3.7s-1.4 3.5-4.4 3.5-4.1-.7-5.8-2l1.6-2.5ZM110 18.5v10.9h-3.3v-5.9l-2.4 3.8h-.2l-2.4-3.8v5.9h-3.4V18.5h3.4l2.5 3.9 2.5-3.9z" className="brand-logo__yellow" />
      <path d="M0 9.4v.1c1 .2 2.3.7 3.8 1.9 2.8 2.3 4.7 7.7 7 13.3h7.7s-3-7.2-4.1-9.7c-1.3-3.2-3.7-5.6-8.1-5.6z" className="brand-logo__cyan" />
      <path d="M15.5 29.3c4.8 0 7.4-4.7 12.3-12.4 2.4-3.8 4-6.5 5.6-8.5 1.9-2.5 5.1-4.7 9.9-6.1v-.1h-9.6c-4.1 0-8 2-10.1 5.3-3 4.7-4.2 6.6-6.6 10.3-1.5 2.3-3.5 3.8-6.5 3.8H5.1c3.7.8 4.8 7.6 10.4 7.6Z" className="brand-logo__cyan" />
      <path d="M25.5 7.8c-3.4 5.3-4.7 7.4-7.4 11.6-1.6 2.6-3.9 4.3-7.3 4.3H7.9c-.8-1-1.7-1.7-2.8-2h5.4c3 0 5-1.6 6.5-3.8 2.4-3.7 3.6-5.6 6.6-10.3 1.7-2.7 4.5-4.6 8-5.1 0 0-3.4 1.2-6.1 5.3" className="brand-logo__yellow" />
      <path d="M39.5 26.6c-.4.2-1 .4-1.8.4-1.3 0-3.1-.9-3.1-3s1-3.2 3-3.2 3 1.3 3 1.3l1.5-2.3c-.7-.6-2.5-1.7-4.6-1.7-3.8 0-6.2 2.9-6.2 5.8 0 4.2 3.4 5.8 6.2 5.8s4.2-1 4.6-1.5V24h-2.6zM77.1 18.5l3.7 5.8v-5.8h3.3v10.8h-3.3l-3.7-5.8v5.8h-3.3V18.5zM54.2 18.5h3.1v10.8h-3.1z" className="brand-logo__cyan" />
      <path d="M56.7 22.7h5V25h-5zM56.7 18.5h5.6V21h-5.6zM56.7 26.9h5.8v2.5h-5.8zM63.8 18.5h3.1v10.8h-3.1z" className="brand-logo__cyan" />
      <path d="M66.3 22.7h5V25h-5zM66.3 18.5h5.6V21h-5.6zM66.3 26.9h5.8v2.5h-5.8zM47.9 26.4h-1.7v2.9h-2.9V18.5h4.9c3.4 0 4.7 2.3 4.7 4.1s-1.1 2.8-2.1 3.4l2.1 3.3h-3.1zm0-5.6h-1.7v3.5H48c1.2 0 2-.7 2-1.7s-.8-1.7-2.1-1.7ZM37.9 23.5h4.2v2.1h-4.2z" className="brand-logo__cyan" />
    </svg>
  );
}

export function BrandGlyph() {
  return (
    <svg viewBox="0 0 44 32" fill="none" aria-hidden="true">
      <path d="M0 9.4v.1c1 .2 2.3.7 3.8 1.9 2.8 2.3 4.7 7.7 7 13.3h7.7s-3-7.2-4.1-9.7c-1.3-3.2-3.7-5.6-8.1-5.6z" fill="currentColor" />
      <path d="M15.5 29.3c4.8 0 7.4-4.7 12.3-12.4 2.4-3.8 4-6.5 5.6-8.5 1.9-2.5 5.1-4.7 9.9-6.1v-.1h-9.6c-4.1 0-8 2-10.1 5.3-3 4.7-4.2 6.6-6.6 10.3-1.5 2.3-3.5 3.8-6.5 3.8H5.1c3.7.8 4.8 7.6 10.4 7.6Z" fill="currentColor" />
      <path d="M25.5 7.8c-3.4 5.3-4.7 7.4-7.4 11.6-1.6 2.6-3.9 4.3-7.3 4.3H7.9c-.8-1-1.7-1.7-2.8-2h5.4c3 0 5-1.6 6.5-3.8 2.4-3.7 3.6-5.6 6.6-10.3 1.7-2.7 4.5-4.6 8-5.1 0 0-3.4 1.2-6.1 5.3" fill="#ffca00" />
    </svg>
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
          <BrandLogo />
          <span className="brand-copy">
            <strong>Customer care</strong>
            <span>GSM-01 · support operations</span>
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
