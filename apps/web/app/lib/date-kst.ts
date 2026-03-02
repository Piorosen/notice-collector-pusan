const KST_TIMEZONE = "Asia/Seoul";

export function getKstDateParts(base = new Date()): { year: number; month: number; day: number } {
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: KST_TIMEZONE,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts(base);
  return {
    year: Number(parts.find((p) => p.type === "year")?.value || "1970"),
    month: Number(parts.find((p) => p.type === "month")?.value || "01"),
    day: Number(parts.find((p) => p.type === "day")?.value || "01"),
  };
}

export function getKstTodayKey(base = new Date()): string {
  const { year, month, day } = getKstDateParts(base);
  return `${year}-${String(month).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
}

export function getKstMonthKey(base = new Date()): string {
  const { year, month } = getKstDateParts(base);
  return `${year}-${String(month).padStart(2, "0")}`;
}

export function getNextMonthKey(monthKey: string): string {
  const [yearRaw, monthRaw] = monthKey.split("-").map(Number);
  const year = yearRaw || 1970;
  const month = monthRaw || 1;
  const next = new Date(year, month, 1);
  return `${next.getFullYear()}-${String(next.getMonth() + 1).padStart(2, "0")}`;
}
