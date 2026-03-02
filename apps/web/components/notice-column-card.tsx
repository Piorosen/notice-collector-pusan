import Link from "next/link";
import SectionCard from "./section-card";

type NoticeItem = {
  id: number;
  source: string;
  title: string;
  link: string;
  author?: string | null;
  published_at?: string | null;
};

type Props = {
  source: string;
  notices: NoticeItem[];
};

const sourceTone: Record<string, string> = {
  cse_notice: "from-violet-300 to-violet-100",
  grad_notice: "from-sky-300 to-sky-100",
  go_grad_notice: "from-cyan-300 to-cyan-100",
  ai_notice: "from-blue-300 to-blue-100",
  aisec_notice: "from-emerald-300 to-emerald-100",
  bk4_notice: "from-orange-300 to-orange-100",
  bk4_repo: "from-fuchsia-300 to-fuchsia-100"
};

export default function NoticeColumnCard({ source, notices }: Props) {
  const gradient = sourceTone[source] || "from-slate-300 to-slate-100";

  return (
    <SectionCard
      className="overflow-hidden p-0"
      right={<span className="rounded-full bg-white/70 px-2 py-1 text-xs font-medium text-slate-700">{notices.length}건</span>}
      title={source}
    >
      <div className={`-mx-4 -mt-4 mb-4 h-2 bg-gradient-to-r ${gradient}`} />
      <ul className="space-y-3">
        {notices.length === 0 && <li className="text-sm text-slate-500">표시할 공지가 없습니다.</li>}
        {notices.map((n) => (
          <li key={n.id} className="rounded-lg border border-slate-100 bg-slate-50 p-3">
            <Link href={`/notices/${n.id}`} className="line-clamp-2 text-sm font-medium text-slate-900 hover:underline">
              {n.title}
            </Link>
            <div className="mt-2 text-xs text-slate-500">
              {n.published_at ? new Date(n.published_at).toLocaleDateString("ko-KR") : "날짜 없음"}
            </div>
          </li>
        ))}
      </ul>
    </SectionCard>
  );
}
