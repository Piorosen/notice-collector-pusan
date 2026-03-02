import Link from "next/link";
import DashboardGrid from "../../../components/dashboard-grid";
import RightWidgets from "../../../components/right-widgets";
import WidgetCard from "../../../components/widget-card";
import { backendFetch } from "../../lib/backend";
import type { DashboardSummary } from "../../lib/types";

type NoticeDetail = {
  id: number;
  source: string;
  title: string;
  link: string;
  author?: string | null;
  published_at?: string | null;
  body_html?: string | null;
  body_text?: string | null;
  images: string[];
  attachments: Array<{ filename: string; local_path: string; source_url: string }>;
};

async function getNotice(id: string): Promise<NoticeDetail | null> {
  try {
    return await backendFetch(`/api/notices/${id}`);
  } catch {
    return null;
  }
}

async function getSummary(): Promise<DashboardSummary | null> {
  try {
    return await backendFetch("/api/dashboard/summary");
  } catch {
    return null;
  }
}

async function getRelated(source: string, excludeId: number) {
  try {
    const list = await backendFetch(`/api/notices?source=${encodeURIComponent(source)}&page=1&page_size=10`);
    return (list as Array<{ id: number; title: string }>).filter((n) => n.id !== excludeId).slice(0, 5);
  } catch {
    return [];
  }
}

async function getNoticesLite() {
  try {
    return await backendFetch("/api/notices?page=1&page_size=20");
  } catch {
    return [];
  }
}

export default async function NoticeDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const notice = await getNotice(id);

  if (!notice) {
    return (
      <main className="space-y-4">
        <p className="text-sm text-slate-600">해당 공지를 찾을 수 없습니다.</p>
        <Link href="/" className="inline-flex rounded-lg bg-slate-900 px-3 py-2 text-sm font-medium text-white">목록으로</Link>
      </main>
    );
  }

  const [summary, notices, related] = await Promise.all([getSummary(), getNoticesLite(), getRelated(notice.source, notice.id)]);

  return (
    <main className="space-y-4">
      <Link href="/" className="inline-flex min-h-10 items-center rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700">목록으로</Link>

      <DashboardGrid
        left={
          <div className="space-y-4">
            <WidgetCard title={notice.title} right={<span className="text-xs text-slate-500">{notice.source}</span>}>
              <div className="mb-3 flex flex-wrap items-center gap-2 text-xs text-slate-500">
                <span>{notice.published_at ? new Date(notice.published_at).toLocaleString("ko-KR") : "게시일 미상"}</span>
                <span className="rounded-full bg-emerald-100 px-2 py-1 font-medium text-emerald-700">본문 캐시됨</span>
                <span className={`rounded-full px-2 py-1 font-medium ${notice.images.length ? "bg-blue-100 text-blue-700" : "bg-slate-100 text-slate-600"}`}>
                  이미지 {notice.images.length}개
                </span>
                <span className={`rounded-full px-2 py-1 font-medium ${notice.attachments.length ? "bg-indigo-100 text-indigo-700" : "bg-slate-100 text-slate-600"}`}>
                  첨부 {notice.attachments.length}개
                </span>
              </div>
              <div className="notice-body prose prose-slate max-w-none" dangerouslySetInnerHTML={{ __html: notice.body_html || "본문 없음" }} />
            </WidgetCard>

            <WidgetCard title="원문 및 첨부">
              <a className="mb-3 block break-all text-sm text-blue-600 underline" href={notice.link} target="_blank">
                {notice.link}
              </a>
              <ul className="space-y-2 text-sm">
                {notice.attachments.length === 0 && <li className="text-slate-500">첨부가 없습니다.</li>}
                {notice.attachments.map((a, idx) => (
                  <li key={`${a.local_path}-${idx}`} className="rounded-md border border-slate-100 bg-slate-50 p-2">
                    <a href={a.source_url} target="_blank" className="font-medium text-blue-700 underline">
                      {a.filename}
                    </a>
                    <p className="mt-1 break-all text-xs text-slate-500">오프라인 경로: {a.local_path}</p>
                  </li>
                ))}
              </ul>
            </WidgetCard>

            <WidgetCard title="관련 공지">
              <ul className="space-y-2 text-sm">
                {related.length === 0 && <li className="text-slate-500">관련 공지가 없습니다.</li>}
                {related.map((r) => (
                  <li key={r.id}>
                    <Link href={`/notices/${r.id}`} className="line-clamp-2 rounded-md bg-slate-50 p-2 text-slate-700 hover:underline" title={r.title}>
                      {r.title}
                    </Link>
                  </li>
                ))}
              </ul>
            </WidgetCard>
          </div>
        }
        right={<RightWidgets summary={summary} totalNotices={notices.length} />}
      />
    </main>
  );
}
