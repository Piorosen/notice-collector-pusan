"use client";

import { useMemo, useState } from "react";

type EventItem = {
  id: number;
  title: string;
  category: string;
  start_date: string;
  end_date: string;
  source_url: string;
};

function toDate(value: string): Date {
  return new Date(`${value}T00:00:00`);
}

function fmtDate(d: Date): string {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

function monthLabel(date: Date): string {
  return `${date.getFullYear()}년 ${date.getMonth() + 1}월`;
}

function categoryLabel(category: string): string {
  if (category === "enroll") return "수강";
  if (category === "exam") return "시험";
  if (category === "graduation") return "졸업";
  if (category === "registration") return "등록";
  return "일반";
}

function categoryColor(category: string): string {
  if (category === "enroll") return "border-blue-200 bg-blue-50 text-blue-700";
  if (category === "exam") return "border-rose-200 bg-rose-50 text-rose-700";
  if (category === "graduation") return "border-amber-200 bg-amber-50 text-amber-700";
  if (category === "registration") return "border-emerald-200 bg-emerald-50 text-emerald-700";
  return "border-slate-200 bg-slate-100 text-slate-700";
}

function dateRangeLabel(event: EventItem): string {
  if (event.start_date === event.end_date) return event.start_date;
  return `${event.start_date} ~ ${event.end_date}`;
}

export default function CalendarMonthView({ events }: { events: EventItem[] }) {
  const today = new Date();
  const [viewDate, setViewDate] = useState(new Date(today.getFullYear(), today.getMonth(), 1));
  const [activeTooltipKey, setActiveTooltipKey] = useState<string | null>(null);

  const gridDays = useMemo(() => {
    const start = new Date(viewDate.getFullYear(), viewDate.getMonth(), 1);
    const startOffset = start.getDay();
    const firstCell = new Date(start);
    firstCell.setDate(start.getDate() - startOffset);
    return Array.from({ length: 42 }, (_, i) => {
      const d = new Date(firstCell);
      d.setDate(firstCell.getDate() + i);
      return d;
    });
  }, [viewDate]);

  const eventsByDate = useMemo(() => {
    const map = new Map<string, EventItem[]>();
    for (const event of events) {
      const start = toDate(event.start_date);
      const end = toDate(event.end_date);
      for (let d = new Date(start); d <= end; d.setDate(d.getDate() + 1)) {
        const key = fmtDate(d);
        if (!map.has(key)) map.set(key, []);
        map.get(key)!.push(event);
      }
    }
    return map;
  }, [events]);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <button
          type="button"
          onClick={() => setViewDate(new Date(viewDate.getFullYear(), viewDate.getMonth() - 1, 1))}
          className="rounded-lg border border-slate-200 px-3 py-1 text-sm text-slate-700 hover:bg-slate-50"
        >
          이전
        </button>
        <h3 className="text-lg font-semibold text-slate-800">{monthLabel(viewDate)}</h3>
        <button
          type="button"
          onClick={() => setViewDate(new Date(viewDate.getFullYear(), viewDate.getMonth() + 1, 1))}
          className="rounded-lg border border-slate-200 px-3 py-1 text-sm text-slate-700 hover:bg-slate-50"
        >
          다음
        </button>
      </div>

      <div className="grid grid-cols-7 gap-2 text-center text-xs font-semibold uppercase tracking-wide text-slate-500">
        {["일", "월", "화", "수", "목", "금", "토"].map((d) => (
          <div key={d}>{d}</div>
        ))}
      </div>

      <div className="grid grid-cols-7 gap-2 overflow-visible">
        {gridDays.map((d, cellIdx) => {
          const key = fmtDate(d);
          const inMonth = d.getMonth() === viewDate.getMonth();
          const isToday = key === fmtDate(today);
          const allEvents = eventsByDate.get(key) || [];
          const dayEvents = allEvents.slice(0, 2);
          const hiddenEventsCount = Math.max(allEvents.length - 2, 0);
          const popupAlignClass = cellIdx % 7 >= 5 ? "right-0" : "left-0";
          const rowIndex = Math.floor(cellIdx / 7);
          const popupVerticalClass = rowIndex >= 4 ? "bottom-full mb-2" : "top-28";

          const dayNumberClass = isToday
            ? "inline-flex h-6 w-6 items-center justify-center rounded-full bg-blue-600 text-white"
            : inMonth
              ? "text-slate-700"
              : "text-slate-400";

          const borderClass = inMonth ? "border-slate-200 bg-white" : "border-slate-100 bg-slate-50";
          return (
            <div
              key={key}
              onMouseEnter={() => setActiveTooltipKey(key)}
              onMouseLeave={() => {
                setActiveTooltipKey((prev) => (prev === key ? null : prev));
              }}
              className={`relative min-h-32 overflow-visible rounded-lg border p-2 text-left transition hover:bg-slate-50 ${borderClass} ${isToday ? "ring-1 ring-blue-300" : ""}`}
            >
              <div className="mb-2 flex items-center justify-between text-xs font-semibold">
                <span className={dayNumberClass}>{d.getDate()}</span>
                <span className="text-[10px] font-medium text-slate-400">{allEvents.length > 0 ? `${allEvents.length}건` : ""}</span>
              </div>
              <div className="space-y-1">
                {dayEvents.map((e) => {
                  const startsToday = e.start_date === key;
                  const continues = !(e.start_date === key && e.end_date === key);

                  return (
                    <div key={`${key}-${e.id}`}>
                      <div
                        className={`rounded-md border px-1.5 py-0.5 text-[11px] leading-4 ${categoryColor(e.category)}`}
                        title={`${e.title} (${dateRangeLabel(e)})`}
                      >
                        <span className="block truncate">{startsToday ? e.title : continues ? "연속 일정" : e.title}</span>
                      </div>
                    </div>
                  );
                })}
                {hiddenEventsCount > 0 ? <div className="text-[11px] text-slate-500">+{hiddenEventsCount}개 더보기</div> : null}
              </div>
              {allEvents.length > 0 && activeTooltipKey === key ? (
                <div className={`absolute z-30 w-[min(20rem,calc(100vw-2rem))] rounded-lg border border-slate-200 bg-white p-3 shadow-xl ${popupAlignClass} ${popupVerticalClass}`}>
                  <div className="mb-2 text-xs font-semibold text-slate-700">{key} 일정 상세</div>
                  <ul className="max-h-64 space-y-2 overflow-auto pr-1">
                    {allEvents.map((event, idx) => (
                      <li key={`${key}-tooltip-${event.id}-${idx}`} className="rounded-md border border-slate-100 bg-slate-50 p-2">
                        <div className="flex items-start justify-between gap-2">
                          <p className="text-xs font-semibold text-slate-800">{event.title}</p>
                          <span className={`shrink-0 rounded-full border px-1.5 py-0.5 text-[10px] font-semibold ${categoryColor(event.category)}`}>
                            {categoryLabel(event.category)}
                          </span>
                        </div>
                        <p className="mt-1 text-[11px] text-slate-500">{dateRangeLabel(event)}</p>
                      </li>
                    ))}
                  </ul>
                </div>
              ) : null}
            </div>
          );
        })}
      </div>
    </div>
  );
}
