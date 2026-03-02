import { ReactNode } from "react";

export default function RightSidebar({ children }: { children: ReactNode }) {
  return <aside className="space-y-4">{children}</aside>;
}
