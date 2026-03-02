import { ReactNode } from "react";

export default function DashboardGrid({ left, right }: { left: ReactNode; right: ReactNode }) {
  return <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_340px]">{left}{right}</div>;
}
