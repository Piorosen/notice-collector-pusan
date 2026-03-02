import AIForm from "../../components/ai-form";
import DashboardGrid from "../../components/dashboard-grid";
import RightWidgets from "../../components/right-widgets";
import WidgetCard from "../../components/widget-card";
import { backendFetch } from "../lib/backend";
import type { DashboardSummary } from "../lib/types";

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

export default async function AIPage() {
  const [summary, notices] = await Promise.all([getSummary(), getNoticesLite()]);

  return (
    <main className="space-y-4">
      <DashboardGrid
        left={
          <WidgetCard title="PNU 공지 AI 질의" right={<span className="text-xs text-slate-500">RAG 기반</span>}>
            <p className="mb-4 text-sm text-slate-600">공지/식단/학사일정 캐시 데이터를 근거로 답변합니다. 출처를 함께 확인하세요.</p>
            <AIForm />
          </WidgetCard>
        }
        right={<RightWidgets summary={summary} totalNotices={notices.length} />}
      />
    </main>
  );
}
