import { ReactNode } from "react";
import SectionHeader from "./section-header";

type Props = {
  title: string;
  right?: ReactNode;
  children: ReactNode;
};

export default function WidgetCard({ title, right, children }: Props) {
  return (
    <section className="rounded-xl border border-slate-200 bg-white shadow-sm">
      <SectionHeader title={title} right={right} />
      <div className="p-4">{children}</div>
    </section>
  );
}
