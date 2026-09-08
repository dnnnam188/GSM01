import type { Metadata, Viewport } from "next";
import { JetBrains_Mono, Manrope } from "next/font/google";
import "./globals.css";

// Không dùng Inter / Roboto / font mặc định trình duyệt — xem
// `.ai/skills/ui-ux-guide.md` và `minimalist-skill`.
// Manrope cho giao diện, JetBrains Mono cho số liệu và siêu dữ liệu.
const sans = Manrope({
  subsets: ["latin", "vietnamese"],
  variable: "--font-sans",
  display: "swap",
});

const mono = JetBrains_Mono({
  subsets: ["latin", "vietnamese"],
  variable: "--font-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: "GreenSM Care · GSM-01",
  description:
    "Không gian hỗ trợ khách hàng và điều phối CSKH GreenSM.",
  icons: {
    icon: [
      {
        url:
          "data:image/svg+xml," +
          encodeURIComponent(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">' +
              '<rect width="32" height="32" rx="7" fill="#2F5D3F"/>' +
              '<path d="M9 21.5V13a4 4 0 0 1 4-4h6a4 4 0 0 1 4 4v8.5" stroke="#fff" ' +
              'stroke-width="2.4" fill="none" stroke-linecap="round"/>' +
              '<circle cx="12" cy="21.5" r="2.1" fill="#fff"/>' +
              '<circle cx="20" cy="21.5" r="2.1" fill="#fff"/></svg>',
          ),
        type: "image/svg+xml",
      },
    ],
  },
};

export const viewport: Viewport = {
  themeColor: "#0e3d2b",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="vi" className={`${sans.variable} ${mono.variable}`}>
      <body>{children}</body>
    </html>
  );
}
