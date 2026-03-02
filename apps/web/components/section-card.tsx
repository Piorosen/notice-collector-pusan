import { ReactNode } from "react";

type Props = {
  title?: string;
  right?: ReactNode;
  children: ReactNode;
  className?: string;
};

export default function SectionCard({ title, right, children, className = "" }: Props) {
  return (
    <section className={`rounded-xl border border-slate-200 bg-white shadow-sm ${className}`.trim()}>
      {(title || right) && (
        <div className="flex items-center justify-between border-b border-slate-100 px-4 py-3">
          {title ? <h2 className="text-sm font-semibold text-slate-900 sm:text-base">{title}</h2> : <div />}
          {right}
        </div>
      )}
      <div className="p-4">{children}</div>
    </section>
  );
}
