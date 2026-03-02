"use client";

import { useState } from "react";

type Citation = {
  source_url?: string | null;
  source_type?: string | null;
  title?: string | null;
  source_key?: string | null;
};

export default function AIForm() {
  const [question, setQuestion] = useState("이번 달 학사일정 핵심만 정리해줘");
  const [answer, setAnswer] = useState("");
  const [citations, setCitations] = useState<Citation[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!question.trim()) {
      setError("질문을 입력해주세요.");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const res = await fetch("/api/ai/query", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question, topK: 6, useAttachments: true })
      });
      if (!res.ok) {
        throw new Error(`AI 질의 실패 (${res.status})`);
      }
      const json = await res.json();
      setAnswer(json.answer || "");
      setCitations(json.citations || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "AI 질의 중 오류가 발생했습니다.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-4">
      <form onSubmit={onSubmit} className="space-y-3">
        <textarea
          rows={5}
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm outline-none ring-blue-200 focus:ring"
          placeholder="질문을 입력하세요"
        />
        <button
          className="inline-flex items-center rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-400"
          disabled={loading}
        >
          {loading ? "질의 중..." : "질의하기"}
        </button>
        {error ? <p className="text-xs text-rose-600">{error}</p> : null}
      </form>

      <div className="grid gap-3 lg:grid-cols-2">
        <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
          <h3 className="mb-2 text-sm font-semibold text-slate-800">답변</h3>
          <p className="whitespace-pre-wrap text-sm text-slate-700">{answer || "-"}</p>
        </div>

        <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
          <h3 className="mb-2 text-sm font-semibold text-slate-800">출처</h3>
          <ul className="space-y-2 text-xs text-slate-600">
            {citations.length === 0 && <li>-</li>}
            {citations.map((c, i) => (
              <li key={`${c.source_key || c.source_url || "src"}-${i}`} className="space-y-1 break-all rounded bg-white px-2 py-1">
                <div className="flex items-center gap-2">
                  <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-semibold text-slate-600">
                    {c.source_type || "unknown"}
                  </span>
                  <span className="line-clamp-1 text-xs font-semibold text-slate-700">{c.title || "제목 없음"}</span>
                </div>
                {c.source_url ? (
                  <a href={c.source_url} target="_blank" rel="noreferrer" className="text-blue-700 underline">
                    {c.source_url}
                  </a>
                ) : <span className="text-slate-500">출처 URL 없음</span>}
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}
