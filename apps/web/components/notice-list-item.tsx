import Link from "next/link";

type NoticeItem = {
  id: number;
  title: string;
  published_at?: string | null;
  has_attachment?: boolean;
};

export default function NoticeListItem({ notice }: { notice: NoticeItem }) {
  return (
    <li className="rounded-lg border border-slate-100 bg-slate-50 p-3">
      <Link href={`/notices/${notice.id}`} className="line-clamp-2 text-sm font-medium text-slate-900 hover:underline" title={notice.title}>
        {notice.title}
      </Link>
      <div className="mt-2 flex items-center justify-between text-xs text-slate-500">
        <span>{notice.published_at ? new Date(notice.published_at).toLocaleDateString("ko-KR") : "날짜 없음"}</span>
        {notice.has_attachment ? <span className="rounded-full bg-blue-100 px-2 py-0.5 text-[10px] font-semibold text-blue-700">첨부</span> : null}
      </div>
    </li>
  );
}
