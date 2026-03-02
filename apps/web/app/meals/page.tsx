import DashboardGrid from "../../components/dashboard-grid";
import MealMonthView from "../../components/meal-month-view";
import RightWidgets from "../../components/right-widgets";
import WidgetCard from "../../components/widget-card";
import { backendFetch } from "../lib/backend";
import { getKstMonthKey, getKstTodayKey, getNextMonthKey } from "../lib/date-kst";
import type { DashboardSummary } from "../lib/types";

type MealRow = {
  date: string;
  cafeteria_key: string;
  cafeteria_name: string;
  breakfast?: string | null;
  lunch?: string | null;
  dinner?: string | null;
};

const cafeterias = [
  { key: "geumjeong_staff", name: "금정회관 교직원 식당" },
  { key: "geumjeong_student", name: "금정회관 학생 식당" },
  { key: "munchang", name: "문창회관 식당" },
  { key: "saetbeol", name: "샛벌회관 식당" },
  { key: "student_hall", name: "학생회관 학생 식당" },
];

async function getMeals(currentMonth: string, nextMonth: string): Promise<MealRow[]> {
  try {
    const [a, b] = await Promise.all([
      backendFetch(`/api/meals?month=${currentMonth}`),
      backendFetch(`/api/meals?month=${nextMonth}`),
    ]);
    const merged = [...a, ...b] as MealRow[];
    const dedup = new Map<string, MealRow>();
    for (const row of merged) {
      dedup.set(`${row.date}|${row.cafeteria_key}`, row);
    }
    return [...dedup.values()].sort((x, y) => x.date.localeCompare(y.date));
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

export default async function MealsPage() {
  const todayKey = getKstTodayKey();
  const currentMonth = getKstMonthKey();
  const nextMonth = getNextMonthKey(currentMonth);
  const [meals, summary, notices] = await Promise.all([getMeals(currentMonth, nextMonth), getSummary(), getNoticesLite()]);

  return (
    <main className="space-y-4">
      <DashboardGrid
        left={
          <WidgetCard title="식단 캘린더 (오늘 기준 2주)">
            <MealMonthView meals={meals} cafeterias={cafeterias} todayKey={todayKey} />
          </WidgetCard>
        }
        right={<RightWidgets summary={summary} totalNotices={notices.length} />}
      />
    </main>
  );
}
