"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { usePathname } from "next/navigation";

const navItems = [
  { href: "/", label: "공지" },
  { href: "/meals", label: "식단" },
  { href: "/calendar", label: "학사일정" },
  { href: "/ai", label: "AI 질의" }
];

const crumbLabel: Record<string, string> = {
  "/": "공지 대시보드",
  "/meals": "식단",
  "/calendar": "학사일정",
  "/ai": "AI 질의"
};

export default function DashboardHeader() {
  const pathname = usePathname();
  const [now, setNow] = useState<Date | null>(null);
  const [lastSync, setLastSync] = useState<string>("-");
  const [weatherLabel, setWeatherLabel] = useState<string>("부산 날씨 불러오는 중...");

  useEffect(() => {
    setNow(new Date());
    const timer = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    let mounted = true;
    const load = async () => {
      try {
        const res = await fetch("/api/dashboard/summary", { cache: "no-store" });
        if (!res.ok) return;
        const json = await res.json();
        if (mounted && json?.last_sync?.updated_at) {
          setLastSync(new Date(json.last_sync.updated_at).toLocaleString("ko-KR"));
        }
      } catch {
        // ignore
      }
    };

    load();
    const timer = setInterval(load, 60000);
    return () => {
      mounted = false;
      clearInterval(timer);
    };
  }, []);

  useEffect(() => {
    let mounted = true;
    const loadWeather = async () => {
      try {
        const res = await fetch("/api/weather", { cache: "no-store" });
        if (!res.ok) return;
        const json = await res.json();
        if (!mounted) return;
        const temp =
          typeof json?.temperature === "number"
            ? `${Math.round(json.temperature * 10) / 10}${json?.temperature_unit || "°C"}`
            : "-";
        setWeatherLabel(`${json?.location || "부산"} ${temp} · ${json?.weather || "날씨 정보 없음"}`);
      } catch {
        if (mounted) setWeatherLabel("부산 날씨 정보 없음");
      }
    };

    loadWeather();
    const timer = setInterval(loadWeather, 10 * 60 * 1000);
    return () => {
      mounted = false;
      clearInterval(timer);
    };
  }, []);

  const timeLabel = useMemo(() => {
    if (!now) return "--:--:--";
    return now.toLocaleString("ko-KR", {
      weekday: "long",
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hour12: false
    });
  }, [now]);

  const breadcrumb = pathname?.startsWith("/notices/") ? "공지 상세" : crumbLabel[pathname || "/"] || "대시보드";

  return (
    <header className="sticky top-0 z-40 border-b border-slate-300/70 bg-sky-100/90 backdrop-blur">
      <div className="mx-auto flex max-w-[1600px] items-center gap-4 px-4 py-3 sm:px-6">
        <div className="min-w-0 flex-1">
          <div className="truncate text-sm font-semibold text-slate-700">PNU Notice Dashboard · {breadcrumb}</div>
          <nav className="mt-1 flex flex-wrap gap-2 text-xs text-slate-700 sm:text-sm">
            {navItems.map((item) => (
              <Link key={item.href} href={item.href} className="rounded-full bg-white/80 px-3 py-1 hover:bg-white">
                {item.label}
              </Link>
            ))}
          </nav>
        </div>

        <div className="hidden text-center text-base font-semibold text-slate-900 md:block">
          {timeLabel}
        </div>

        <div className="ml-auto rounded-full bg-white/85 px-3 py-1 text-xs font-medium text-slate-700 sm:text-sm">
          {weatherLabel} · 최근 동기화 {lastSync}
        </div>
      </div>
    </header>
  );
}
