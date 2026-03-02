import RightSidebar from "./right-sidebar";
import WidgetCard from "./widget-card";
import StatChip from "./stat-chip";
import SyncStatusWidget from "./sync-status-widget";
import type { DashboardSummary } from "../app/lib/types";

export default function RightWidgets({ summary, totalNotices }: { summary: DashboardSummary | null; totalNotices: number }) {
  const todayMeal = summary?.today_meals;
  const todayByCafe = summary?.today_meals_by_cafeteria || [];
  const preferredCafe =
    todayByCafe.find((c) => c.cafeteria_key === "geumjeong_student")
    || todayByCafe.find((c) => c.cafeteria_name.includes("금정회관 학생"))
    || null;

  return (
    <RightSidebar>
      <WidgetCard title="오늘 상태">
        <div className="grid grid-cols-2 gap-2">
          <StatChip label="오늘 공지" value={summary?.today_notice_count ?? 0} tone="blue" />
          <StatChip label="전체 공지" value={totalNotices} tone="slate" />
        </div>
      </WidgetCard>

      <WidgetCard title="오늘 식단 요약">
        {preferredCafe && (
          <ul className="mb-3 space-y-2 text-sm">
            <li key={preferredCafe.cafeteria_key} className="rounded-md bg-slate-50 p-2">
              <p className="mb-1 text-xs font-semibold text-slate-600">{preferredCafe.cafeteria_name}</p>
              <p className="line-clamp-1"><strong className="mr-2">조식</strong>{preferredCafe.breakfast || "-"}</p>
              <p className="line-clamp-1"><strong className="mr-2">중식</strong>{preferredCafe.lunch || "-"}</p>
              <p className="line-clamp-1"><strong className="mr-2">석식</strong>{preferredCafe.dinner || "-"}</p>
            </li>
          </ul>
        )}
        {!preferredCafe && !todayMeal && <p className="text-sm text-slate-500">금정회관 학생식당 식단 정보가 없습니다.</p>}
        {!preferredCafe && todayMeal && (
          <ul className="space-y-2 text-sm">
            <li><strong className="mr-2">조식</strong>{todayMeal.breakfast || "-"}</li>
            <li><strong className="mr-2">중식</strong>{todayMeal.lunch || "-"}</li>
            <li><strong className="mr-2">석식</strong>{todayMeal.dinner || "-"}</li>
          </ul>
        )}
      </WidgetCard>

      <WidgetCard title="인기 공지">
        <ul className="space-y-2 text-sm text-slate-700">
          {(summary?.top_notices || []).slice(0, 6).map((n) => (
            <li key={n.id} className="line-clamp-2 rounded-md bg-slate-50 p-2" title={n.title}>
              {n.title}
            </li>
          ))}
          {!summary?.top_notices?.length && <li className="text-slate-500">표시할 공지가 없습니다.</li>}
        </ul>
      </WidgetCard>

      <WidgetCard title="최근 동기화 상태">
        <SyncStatusWidget lastSync={summary?.last_sync} />
      </WidgetCard>

      <WidgetCard title="소스별 수집 건수">
        <ul className="space-y-1 text-sm">
          {(summary?.source_stats || []).map((s) => (
            <li key={s.source} className="flex items-center justify-between rounded bg-slate-50 px-2 py-1">
              <span className="truncate text-slate-700" title={s.source_display_name || s.source}>{s.source_display_name || s.source}</span>
              <span className="font-semibold text-slate-900">{s.count}</span>
            </li>
          ))}
        </ul>
      </WidgetCard>
    </RightSidebar>
  );
}
