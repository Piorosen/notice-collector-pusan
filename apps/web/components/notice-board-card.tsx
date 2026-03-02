import WidgetCard from "./widget-card";
import NoticeListItem from "./notice-list-item";

type NoticeItem = {
  id: number;
  source: string;
  source_display_name?: string;
  title: string;
  link: string;
  author?: string | null;
  published_at?: string | null;
  has_attachment?: boolean;
};

type Props = {
  source: string;
  sourceDisplayName?: string;
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

export default function NoticeBoardCard({ source, sourceDisplayName, notices }: Props) {
  const gradient = sourceTone[source] || "from-slate-300 to-slate-100";

  return (
    <WidgetCard
      title={sourceDisplayName || source}
      right={<span className="rounded-full bg-white/70 px-2 py-1 text-xs font-medium text-slate-700">{notices.length}건</span>}
    >
      <div className={`-mx-4 -mt-4 mb-4 h-2 bg-gradient-to-r ${gradient}`} />
      <ul className="max-h-[720px] space-y-3 overflow-y-auto pr-1">
        {notices.length === 0 && <li className="text-sm text-slate-500">표시할 공지가 없습니다.</li>}
        {notices.map((n) => (
          <NoticeListItem key={n.id} notice={n} />
        ))}
      </ul>
    </WidgetCard>
  );
}
