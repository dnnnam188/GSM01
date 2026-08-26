import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "GSM-01 · Trợ lý CSKH Xanh SM",
  description: "AI Agent tiếp nhận yêu cầu đặt xe và xử lý khiếu nại",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="vi">
      <body>{children}</body>
    </html>
  );
}
