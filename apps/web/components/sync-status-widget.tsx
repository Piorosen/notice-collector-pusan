"use client";

import { useEffect, useMemo, useState } from "react";

type LastSync = {
  job_id?: number | null;
  status?: string;
  updated_at?: string | null;
  message?: string | null;
  current_source?: string | null;
  stage_current?: string | null;
  progress_total_pages?: number;
  progress_done_pages?: number;
  stage_total?: number;
  stage_done?: number;
};

type SyncStatus = {
  job_id: number;
  target: string;
  status: string;
  message?: string | null;
  progress_total_pages: number;
  progress_done_pages: number;
  stage_total: number;
  stage_done: number;
  stage_current?: string | null;
  current_source?: string | null;
  error_count: number;
  updated_at?: string;
};

function wait(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

const SOURCE_LABELS: Record<string, string> = {
  cse_notice: "컴퓨터공학과 공지",
  grad_notice: "일반대학원 공지",
  go_grad_notice: "대학원 입학 공지",
  ai_notice: "AI 대학원 공지",
  aisec_notice: "융합보안대학원 공지",
  bk4_notice: "BK4-ICE 공지",
  bk4_repo: "BK4-ICE 자료실",
  meals: "식단",
  calendar: "학사일정",
  notices: "공지사항",
};

function displaySource(value?: string | null): string {
  if (!value) return "-";
  return SOURCE_LABELS[value] || value;
}

export default function SyncStatusWidget({ lastSync }: { lastSync?: LastSync }) {
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState<SyncStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);

  useEffect(() => {
    if (!lastSync?.job_id || lastSync.status !== "running") return;
    let active = true;
    const interval = setInterval(async () => {
      try {
        const res = await fetch(`/api/sync/status/${lastSync.job_id}`, { cache: "no-store" });
        if (!res.ok) return;
        const s = (await res.json()) as SyncStatus;
        if (!active) return;
        setStatus(s);
        if (s.status === "completed" || s.status === "failed") clearInterval(interval);
      } catch {
        // no-op
      }
    }, 1500);
    return () => {
      active = false;
      clearInterval(interval);
    };
  }, [lastSync?.job_id, lastSync?.status]);

  const percent = useMemo(() => {
    const s = status || (lastSync as SyncStatus | undefined);
    if (!s) return 0;
    if (s.progress_total_pages > 0) {
      return Math.min(100, Math.round((s.progress_done_pages / s.progress_total_pages) * 100));
    }
    if (s.stage_total > 0) {
      return Math.min(100, Math.round((s.stage_done / s.stage_total) * 100));
    }
    return s.status === "completed" ? 100 : 0;
  }, [status, lastSync]);

  async function runSync(target: "all" | "notices" | "meals" | "calendar") {
    try {
      setError(null);
      setInfo(null);
      setLoading(true);
      const runRes = await fetch("/api/sync/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ target, backfill: false }),
      });
      if (!runRes.ok) throw new Error("sync run failed");
      const runData = await runRes.json();
      if (runData.no_op) {
        setStatus(null);
        setError(null);
        setInfo(runData.message || "최근 완료 이력이 있어 동기화를 건너뛰었습니다.");
        return;
      }
      const jobId = runData.job_id;
      if (!jobId) throw new Error("job id not found");

      for (let i = 0; i < 600; i += 1) {
        const res = await fetch(`/api/sync/status/${jobId}`, { cache: "no-store" });
        if (!res.ok) throw new Error("status fetch failed");
        const s = (await res.json()) as SyncStatus;
        setStatus(s);
        if (s.status === "completed" || s.status === "failed") break;
        await wait(1200);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "동기화 요청 실패");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-3 text-sm text-slate-600">
      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          onClick={() => runSync("all")}
          disabled={loading}
          className="rounded-md bg-blue-600 px-3 py-1.5 text-xs font-semibold text-white disabled:opacity-60"
        >
          전체 동기화
        </button>
        <button
          type="button"
          onClick={() => runSync("notices")}
          disabled={loading}
          className="rounded-md border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 disabled:opacity-60"
        >
          공지
        </button>
        <button
          type="button"
          onClick={() => runSync("meals")}
          disabled={loading}
          className="rounded-md border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 disabled:opacity-60"
        >
          식단
        </button>
        <button
          type="button"
          onClick={() => runSync("calendar")}
          disabled={loading}
          className="rounded-md border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 disabled:opacity-60"
        >
          학사일정
        </button>
      </div>

      <div>
        <p>상태: <strong className="text-slate-800">{status?.status || lastSync?.status || "unknown"}</strong></p>
        <p>현재: {displaySource(status?.current_source || status?.stage_current || lastSync?.current_source || lastSync?.stage_current)}</p>
        <p>
          진행: {status ? `${status.progress_done_pages}/${status.progress_total_pages || 0} 페이지` : `${lastSync?.progress_done_pages ?? 0}/${lastSync?.progress_total_pages ?? 0} 페이지`}
          {(status?.stage_total || lastSync?.stage_total) ? ` · 단계 ${status?.stage_done ?? lastSync?.stage_done ?? 0}/${status?.stage_total ?? lastSync?.stage_total ?? 0}` : ""}
        </p>
        <p>시각: {status?.updated_at ? new Date(status.updated_at).toLocaleString("ko-KR") : lastSync?.updated_at ? new Date(lastSync.updated_at).toLocaleString("ko-KR") : "-"}</p>
      </div>

      <div className="h-2 w-full overflow-hidden rounded-full bg-slate-100">
        <div className="h-full bg-blue-500 transition-all" style={{ width: `${percent}%` }} />
      </div>

      {status?.message ? <p className="line-clamp-3 text-xs text-slate-500">{status.message}</p> : null}
      {info ? <p className="text-xs text-emerald-700">{info}</p> : null}
      {error ? <p className="text-xs text-rose-600">{error}</p> : null}
    </div>
  );
}
