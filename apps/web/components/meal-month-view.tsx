"use client";

import { useEffect, useMemo, useState } from "react";

type MealRow = {
  date: string;
  cafeteria_key: string;
  cafeteria_name: string;
  breakfast?: string | null;
  lunch?: string | null;
  dinner?: string | null;
};

type Cafeteria = {
  key: string;
  name: string;
};

const WEEKDAYS = ["일", "월", "화", "수", "목", "금", "토"] as const;

function fmtDate(d: Date): string {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

function parseDateKey(value: string): Date {
  const [year, month, day] = value.split("-").map(Number);
  return new Date(year, (month || 1) - 1, day || 1);
}

function addDays(date: Date, days: number): Date {
  const next = new Date(date);
  next.setDate(next.getDate() + days);
  return next;
}

export default function MealMonthView({
  meals,
  cafeterias,
  todayKey,
}: {
  meals: MealRow[];
  cafeterias: Cafeteria[];
  todayKey: string;
}) {
  const availableKeys = useMemo(() => {
    const set = new Set(meals.map((m) => m.cafeteria_key));
    return cafeterias.filter((c) => set.has(c.key)).map((c) => c.key);
  }, [meals, cafeterias]);

  const defaultKey = availableKeys[0] || cafeterias[0]?.key || "";
  const [selectedKey, setSelectedKey] = useState(defaultKey);

  const selectedCafeteria = cafeterias.find((c) => c.key === selectedKey);
  const selectedMeals = useMemo(() => meals.filter((m) => m.cafeteria_key === selectedKey), [meals, selectedKey]);
  const [selectedDateKey, setSelectedDateKey] = useState("");

  const mealsByDate = useMemo(() => {
    const map = new Map<string, MealRow>();
    for (const meal of selectedMeals) map.set(meal.date, meal);
    return map;
  }, [selectedMeals]);

  const today = parseDateKey(todayKey);

  const twoWeekKeys = useMemo(() => {
    return Array.from({ length: 14 }, (_, i) => fmtDate(addDays(today, i)));
  }, [today]);
  const leadingEmptyCells = useMemo(() => parseDateKey(twoWeekKeys[0] || todayKey).getDay(), [twoWeekKeys, todayKey]);
  const calendarCells = useMemo(() => {
    const empty = Array.from({ length: leadingEmptyCells }, (_, idx) => `__empty__${idx}`);
    return [...empty, ...twoWeekKeys];
  }, [leadingEmptyCells, twoWeekKeys]);

  useEffect(() => {
    if (twoWeekKeys.length === 0) return;
    if (!selectedDateKey || !twoWeekKeys.includes(selectedDateKey)) {
      setSelectedDateKey(twoWeekKeys.includes(todayKey) ? todayKey : twoWeekKeys[0]);
    }
  }, [selectedDateKey, twoWeekKeys, todayKey]);

  const selectedMeal = mealsByDate.get(selectedDateKey);
  const windowLabel = twoWeekKeys.length > 0 ? `${twoWeekKeys[0]} ~ ${twoWeekKeys[twoWeekKeys.length - 1]}` : "-";

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-2">
        {cafeterias.map((cafeteria) => {
          const active = cafeteria.key === selectedKey;
          const hasData = availableKeys.includes(cafeteria.key);
          return (
            <button
              key={cafeteria.key}
              type="button"
              onClick={() => setSelectedKey(cafeteria.key)}
              className={`rounded-full border px-3 py-1.5 text-xs font-semibold transition sm:text-sm ${active ? "border-blue-500 bg-blue-50 text-blue-700" : "border-slate-200 bg-white text-slate-700 hover:bg-slate-50"} ${hasData ? "" : "opacity-60"}`}
            >
              {cafeteria.name}
            </button>
          );
        })}
      </div>

      <div className="rounded-xl border border-slate-200 bg-slate-50 p-3">
        <div className="flex items-center justify-between">
          <h3 className="text-base font-semibold text-slate-800 sm:text-lg">{selectedCafeteria?.name || "식당"} 식단</h3>
          <span className="rounded-full bg-white px-3 py-1 text-xs font-medium text-slate-600">오늘 기준 2주</span>
        </div>
        <p className="mt-2 text-xs text-slate-500">{windowLabel}</p>
      </div>

      <div className="grid grid-cols-7 gap-2 text-center text-xs font-semibold uppercase tracking-wide text-slate-500">
        {["일", "월", "화", "수", "목", "금", "토"].map((day) => (
          <div key={day}>{day}</div>
        ))}
      </div>

      <div className="rounded-xl border border-slate-200 bg-slate-50 p-3">
        <div className="flex items-center justify-between">
          <h4 className="text-sm font-semibold text-slate-800">{selectedDateKey || todayKey} 상세 식단</h4>
          <span className="rounded-full bg-white px-2 py-1 text-xs font-medium text-slate-600">{selectedCafeteria?.name || "식당"}</span>
        </div>
        {selectedMeal ? (
          <div className="mt-3 grid gap-2 md:grid-cols-3">
            <MealDetail title="조식" value={selectedMeal.breakfast} />
            <MealDetail title="중식" value={selectedMeal.lunch} />
            <MealDetail title="석식" value={selectedMeal.dinner} />
          </div>
        ) : (
          <p className="mt-3 text-sm text-slate-500">선택한 날짜의 식단 데이터가 없습니다.</p>
        )}
      </div>

      <div className="grid grid-cols-7 gap-2">
        {calendarCells.map((key) => {
          if (key.startsWith("__empty__")) {
            return <div key={key} className="min-h-28 rounded-lg border border-transparent bg-transparent p-2" aria-hidden="true" />;
          }
          const day = parseDateKey(key);
          const isToday = key === todayKey;
          const meal = mealsByDate.get(key);
          const isSelected = key === selectedDateKey;
          const mealCount = [meal?.breakfast, meal?.lunch, meal?.dinner].filter((m) => m && m.trim()).length;
          return (
            <button
              type="button"
              onClick={() => setSelectedDateKey(key)}
              key={key}
              className={`min-h-28 rounded-lg border border-slate-200 bg-white p-2 text-left transition ${isToday ? "ring-1 ring-blue-300" : ""} ${isSelected ? "ring-2 ring-sky-300" : "hover:bg-slate-50"}`}
            >
              <div className="mb-2 flex items-center justify-between">
                <span className="text-xs font-semibold text-slate-700">
                  {day.getMonth() + 1}/{day.getDate()} ({WEEKDAYS[day.getDay()]})
                </span>
                <span className="text-[10px] font-medium text-slate-400">
                  {isToday ? "TODAY" : mealCount > 0 ? `${mealCount}식` : ""}
                </span>
              </div>

              {meal ? (
                <div className="space-y-1 text-[11px] text-slate-700">
                  <MealPreview label="조" value={meal.breakfast} />
                  <MealPreview label="중" value={meal.lunch} />
                  <MealPreview label="석" value={meal.dinner} />
                </div>
              ) : (
                <div className="pt-3 text-[11px] text-slate-400">식단 없음</div>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}

function MealPreview({ label, value }: { label: string; value?: string | null }) {
  const hasMenu = Boolean(value && value.trim());
  return (
    <div className="flex items-center gap-1.5">
      <span className="rounded bg-slate-100 px-1.5 py-0.5 text-[10px] font-semibold text-slate-600">{label}</span>
      <span
        className={`rounded-full px-2 py-0.5 text-[10px] font-semibold ${hasMenu ? "bg-emerald-100 text-emerald-700" : "bg-slate-100 text-slate-500"}`}
        title={hasMenu ? "상세 메뉴는 하단 상세 카드에서 확인" : "메뉴 없음"}
      >
        {hasMenu ? "메뉴 있음" : "없음"}
      </span>
    </div>
  );
}

function MealDetail({ title, value }: { title: string; value?: string | null }) {
  const text = value && value.trim() ? value : "정보 없음";
  const normalized = text
    .replace(/\r/g, "\n")
    .replace(/\s*\/\s*/g, "\n")
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);
  const tags = extractMealTags(normalized.join(" "));
  const hasNoData = normalized.length === 0 || normalized[0] === "정보 없음";

  return (
    <section className="rounded-lg border border-slate-200 bg-white p-3">
      <h5 className="text-xs font-semibold text-slate-700">{title}</h5>
      {!hasNoData && (tags.categories.length > 0 || tags.alerts.length > 0) ? (
        <div className="mt-2 flex flex-wrap gap-1">
          {tags.categories.map((tag) => (
            <span key={`${title}-cat-${tag}`} className="rounded-full bg-blue-100 px-2 py-0.5 text-[10px] font-semibold text-blue-700">
              {tag}
            </span>
          ))}
          {tags.alerts.map((tag) => (
            <span key={`${title}-warn-${tag}`} className="rounded-full bg-amber-100 px-2 py-0.5 text-[10px] font-semibold text-amber-700">
              {tag}
            </span>
          ))}
        </div>
      ) : null}
      {hasNoData ? (
        <p className="mt-1 text-sm leading-6 text-slate-500">정보 없음</p>
      ) : (
        <ul className="mt-2 space-y-1 text-sm leading-6 text-slate-800">
          {normalized.map((line, idx) => (
            <li key={`${title}-${idx}`} className="rounded bg-slate-50 px-2 py-1">
              {line}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function extractMealTags(text: string): { categories: string[]; alerts: string[] } {
  const source = text.toLowerCase();
  const categories: string[] = [];
  const alerts: string[] = [];

  const categoryRules: Array<{ label: string; patterns: RegExp[] }> = [
    { label: "밥류", patterns: [/밥|비빔|덮밥|볶음밥|카레/] },
    { label: "면류", patterns: [/면|라면|우동|파스타|국수|쫄면/] },
    { label: "국물", patterns: [/국|찌개|탕|스프/] },
    { label: "육류", patterns: [/돈까스|제육|불고기|닭|치킨|돼지|소고기/] },
    { label: "해산물", patterns: [/생선|오징어|새우|해물|고등어/] },
    { label: "샐러드", patterns: [/샐러드/] },
  ];

  for (const rule of categoryRules) {
    if (rule.patterns.some((pattern) => pattern.test(source))) categories.push(rule.label);
  }

  const allergenNumberMap: Record<string, string> = {
    "1": "난류",
    "2": "우유",
    "3": "메밀",
    "4": "땅콩",
    "5": "대두",
    "6": "밀",
    "7": "고등어",
    "8": "게",
    "9": "새우",
    "10": "돼지고기",
    "11": "복숭아",
    "12": "토마토",
    "13": "아황산류",
    "14": "호두",
    "15": "닭고기",
    "16": "쇠고기",
    "17": "오징어",
    "18": "조개류",
  };

  const foundNums = new Set<string>();
  const numMatches = text.match(/\b([1-9]|1[0-8])\b/g) || [];
  for (const n of numMatches) {
    if (allergenNumberMap[n]) foundNums.add(n);
  }
  for (const n of [...foundNums].sort((a, b) => Number(a) - Number(b))) {
    alerts.push(`알레르기 ${allergenNumberMap[n]}`);
  }

  const allergenWordRules: Array<{ key: string; label: string }> = [
    { key: "우유", label: "알레르기 우유" },
    { key: "대두", label: "알레르기 대두" },
    { key: "밀", label: "알레르기 밀" },
    { key: "땅콩", label: "알레르기 땅콩" },
    { key: "난류", label: "알레르기 난류" },
    { key: "새우", label: "알레르기 새우" },
  ];
  for (const rule of allergenWordRules) {
    if (text.includes(rule.key) && !alerts.includes(rule.label)) alerts.push(rule.label);
  }

  return {
    categories: [...new Set(categories)].slice(0, 3),
    alerts: [...new Set(alerts)].slice(0, 4),
  };
}
