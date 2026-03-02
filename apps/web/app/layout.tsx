import "./globals.css";
import type { Metadata } from "next";
import DashboardHeader from "../components/dashboard-header";

export const metadata: Metadata = {
  title: "PNU Notice Dashboard",
  description: "부산대학교 공지사항/식단/학사일정 통합 대시보드"
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko">
      <body className="min-h-screen text-slate-900 antialiased">
        <DashboardHeader />
        <div className="mx-auto w-full max-w-[1600px] px-4 py-6 sm:px-6">{children}</div>
      </body>
    </html>
  );
}
