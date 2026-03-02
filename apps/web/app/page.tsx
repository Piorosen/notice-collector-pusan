import DashboardGrid from "../components/dashboard-grid";
import NoticeBoardCard from "../components/notice-board-card";
import RightWidgets from "../components/right-widgets";
import WidgetCard from "../components/widget-card";
import { backendFetch } from "./lib/backend";
import type { DashboardSummary } from "./lib/types";

type Notice = {
  id: number;
  source: string;
  source_display_name?: string;
  title: string;
  link: string;
  author?: string | null;
  published_at?: string | null;
  has_attachment?: boolean;
  has_image?: boolean;
};

const sourceOrder = [
  "cse_notice",
  "grad_notice",
  "go_grad_notice",
  "ai_notice",
  "aisec_notice",
  "bk4_notice",
  "bk4_repo"
];

function asArray(param: string | string[] | undefined): string[] {
  if (!param) return [];
  return Array.isArray(param) ? param : [param];
}

async function getNotices(queryString: string): Promise<Notice[]> {
  try {
    return await backendFetch(`/api/notices${queryString ? `?${queryString}` : ""}`);
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

export default async function HomePage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const params = await searchParams;
  const selectedSources = asArray(params.source).filter(Boolean);

  const urlParams = new URLSearchParams();
  if (params.q) urlParams.set("q", String(params.q));
  if (params.from) urlParams.set("from", String(params.from));
  if (params.to) urlParams.set("to", String(params.to));
  if (params.sort) urlParams.set("sort", String(params.sort));
  if (params.hasAttachment === "true") urlParams.set("hasAttachment", "true");
  if (params.hasImage === "true") urlParams.set("hasImage", "true");
  for (const s of selectedSources) urlParams.append("source", s);
  urlParams.set("page", "1");
  urlParams.set("page_size", "300");

  const [notices, summary] = await Promise.all([getNotices(urlParams.toString()), getSummary()]);

  const sourceLabel = new Map<string, string>();
  for (const item of summary?.source_stats || []) {
    sourceLabel.set(item.source, item.source_display_name || item.source);
  }
  for (const n of notices) {
    if (n.source_display_name) sourceLabel.set(n.source, n.source_display_name);
  }

  const grouped = new Map<string, Notice[]>();
  for (const key of sourceOrder) grouped.set(key, []);
  for (const n of notices) {
    if (!grouped.has(n.source)) grouped.set(n.source, []);
    grouped.get(n.source)!.push(n);
  }

  const sourceOptions = sourceOrder
    .filter((key) => grouped.has(key) || sourceLabel.has(key))
    .map((key) => ({ key, label: sourceLabel.get(key) || key }));

  return (
    <main className="space-y-6">
      <WidgetCard title="공지 통합 뷰" right={<span className="text-xs text-slate-500">소스별 멀티컬럼</span>}>
        <form className="grid gap-3 lg:grid-cols-12" method="get" aria-label="공지 필터">
          <div className="lg:col-span-4">
            <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-600">검색어</label>
            <input
              type="text"
              name="q"
              defaultValue={params.q ? String(params.q) : ""}
              placeholder="제목/본문 검색"
              className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm outline-none ring-blue-200 focus:ring"
            />
          </div>

          <div className="lg:col-span-2">
            <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-600">From</label>
            <input
              type="date"
              name="from"
              defaultValue={params.from ? String(params.from) : ""}
              className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm outline-none ring-blue-200 focus:ring"
            />
          </div>

          <div className="lg:col-span-2">
            <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-600">To</label>
            <input
              type="date"
              name="to"
              defaultValue={params.to ? String(params.to) : ""}
              className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm outline-none ring-blue-200 focus:ring"
            />
          </div>

          <div className="lg:col-span-2">
            <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-600">정렬</label>
            <select
              name="sort"
              defaultValue={params.sort ? String(params.sort) : "recent"}
              className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm outline-none ring-blue-200 focus:ring"
            >
              <option value="recent">최신순</option>
              <option value="popular">인기순(첨부 우선)</option>
            </select>
          </div>

          <div className="flex items-end gap-2 lg:col-span-2">
            <button type="submit" className="inline-flex min-h-10 w-full items-center justify-center rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800">
              적용
            </button>
          </div>

          <div className="lg:col-span-12">
            <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-600">소스 선택</div>
            <div className="flex flex-wrap gap-2">
              {sourceOptions.map((s) => {
                const active = selectedSources.includes(s.key);
                return (
                  <label key={s.key} className={`inline-flex min-h-10 cursor-pointer items-center gap-2 rounded-full border px-3 py-2 text-sm ${active ? "border-blue-300 bg-blue-50 text-blue-700" : "border-slate-200 bg-white text-slate-700"}`}>
                    <input type="checkbox" name="source" value={s.key} defaultChecked={active} className="h-4 w-4 rounded border-slate-300" />
                    {s.label}
                  </label>
                );
              })}
              <label className={`inline-flex min-h-10 cursor-pointer items-center gap-2 rounded-full border px-3 py-2 text-sm ${params.hasAttachment === "true" ? "border-blue-300 bg-blue-50 text-blue-700" : "border-slate-200 bg-white text-slate-700"}`}>
                <input type="checkbox" name="hasAttachment" value="true" defaultChecked={params.hasAttachment === "true"} className="h-4 w-4 rounded border-slate-300" />
                첨부 포함만
              </label>
              <label className={`inline-flex min-h-10 cursor-pointer items-center gap-2 rounded-full border px-3 py-2 text-sm ${params.hasImage === "true" ? "border-blue-300 bg-blue-50 text-blue-700" : "border-slate-200 bg-white text-slate-700"}`}>
                <input type="checkbox" name="hasImage" value="true" defaultChecked={params.hasImage === "true"} className="h-4 w-4 rounded border-slate-300" />
                이미지 포함만
              </label>
            </div>
          </div>
        </form>
      </WidgetCard>

      <DashboardGrid
        left={
          <section>
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4">
              {Array.from(grouped.entries()).map(([source, list]) => (
                <NoticeBoardCard key={source} source={source} sourceDisplayName={sourceLabel.get(source)} notices={list.slice(0, 25)} />
              ))}
            </div>
          </section>
        }
        right={<RightWidgets summary={summary} totalNotices={notices.length} />}
      />
    </main>
  );
}
