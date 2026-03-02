import { ReactNode } from "react";

type Props = {
  title: string;
  right?: ReactNode;
};

export default function SectionHeader({ title, right }: Props) {
  return (
    <div className="flex items-center justify-between border-b border-slate-100 px-4 py-3">
      <h2 className="text-sm font-semibold text-slate-900 sm:text-base">{title}</h2>
      {right}
    </div>
  );
}
