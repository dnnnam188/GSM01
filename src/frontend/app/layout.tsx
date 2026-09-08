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
              '<rect width="32" height="32" rx="7" fill="#2dccd3"/>' +
              '<path d="M4.5 11c2.6.6 4 3.3 5.4 6.7h4.6s-1.8-4.3-2.5-5.8C11 10 9.6 8.8 7 8.8H4.5Z" fill="#fff"/>' +
              '<path d="M13.8 22.2c2.9 0 4.5-2.8 7.4-7.5 1.5-2.3 2.4-3.9 3.4-5.1 1.1-1.5 3.1-2.8 6-3.7h-5.8c-2.5 0-4.8 1.2-6.1 3.2-1.8 2.8-2.5 4-4 6.2-.9 1.4-2.1 2.3-3.9 2.3H7.5c2.2.5 2.9 4.6 6.3 4.6Z" fill="#fff"/>' +
              '<path d="M20 9.2c-2.1 3.2-2.8 4.5-4.5 7-1 1.5-2.4 2.6-4.4 2.6H9.2c-.5-.6-1-.9-1.7-1.2h3.3c1.8 0 3-.9 3.9-2.3 1.5-2.2 2.2-3.4 4-6.2 1-1.6 2.7-2.8 4.8-3.1 0 0-2 .7-3.5 3.2Z" fill="#ffca00"/></svg>',
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
