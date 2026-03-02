import CalendarMonthView from "../../components/calendar-month-view";
import DashboardGrid from "../../components/dashboard-grid";
import RightWidgets from "../../components/right-widgets";
import WidgetCard from "../../components/widget-card";
import { backendFetch } from "../lib/backend";
import type { DashboardSummary } from "../lib/types";

type EventItem = {
  id: number;
  title: string;
  category: string;
  start_date: string;
  end_date: string;
  source_url: string;
};

const year = new Date().getFullYear();

async function getCalendar(): Promise<EventItem[]> {
  try {
    return await backendFetch(`/api/calendar?year=${year}`);
  } catch {
    return [];
  }
}

async function getSummary(): Promise<DashboardSummary | null> {
  try {
    return await backendFetch("/api/dashboard/summary");
  } catch {
    return null;
  }
}

async function getNoticesLite() {
  try {
    return await backendFetch("/api/notices?page=1&page_size=20");
  } catch {
    return [];
  }
}

export default async function CalendarPage() {
  const [events, summary, notices] = await Promise.all([getCalendar(), getSummary(), getNoticesLite()]);

  return (
    <main className="space-y-4">
      <DashboardGrid
        left={
          <WidgetCard
            title={`학사일정 캘린더 (${year}) · ${events.length}건`}
            right={
              <a className="text-xs text-slate-500 underline" href="https://his.pusan.ac.kr/style-guide/19273/subview.do" target="_blank">
                출처 보기
              </a>
            }
          >
            <CalendarMonthView events={events} />
          </WidgetCard>
        }
        right={<RightWidgets summary={summary} totalNotices={notices.length} />}
      />
    </main>
  );
}
