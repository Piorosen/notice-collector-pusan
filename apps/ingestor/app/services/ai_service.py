from openai import OpenAI
from sqlalchemy.orm import Session

from ..config import settings
from .rag_indexer import rag_indexer


SYSTEM_PROMPT = """당신은 부산대학교 공지사항 도우미입니다.
반드시 제공된 근거 범위 안에서만 답하세요.
근거가 부족하면 '확인된 정보가 부족합니다.'라고 답하세요.
"""


class AIService:
    def __init__(self) -> None:
        self.client = OpenAI(api_key=settings.OPENAI_KEY) if settings.OPENAI_KEY else None

    def refresh_missing_embeddings(self, db: Session, limit: int = 50) -> int:
        return rag_indexer.refresh_missing_embeddings(db, limit=limit)

    def answer(self, db: Session, question: str, top_k: int = 6, use_attachments: bool = True) -> tuple[str, list[dict]]:
        docs = rag_indexer.search_chunks(db, question, top_k * 2)
        if not use_attachments:
            docs = [d for d in docs if d.source_type not in ("attachment_text", "attachment_meta")]
        docs = docs[:top_k]
        raw_citations = [
            {
                "source_url": d.source_url,
                "source_type": d.source_type,
                "title": d.title,
                "source_key": d.source_key,
            }
            for d in docs
        ]
        seen_keys: set[str] = set()
        citations: list[dict] = []
        for c in raw_citations:
            key = c.get("source_key") or c.get("source_url") or ""
            if key and key in seen_keys:
                continue
            if key:
                seen_keys.add(key)
            citations.append(c)

        if not docs:
            return "확인된 정보가 부족합니다.", citations

        if not self.client:
            # 키가 없을 때 기본 동작
            summary = "\n".join([f"- {d.chunk_text[:180]}" for d in docs[:5]])
            return f"OpenAI 키가 없어 캐시 기반 요약만 제공합니다.\n{summary}", citations

        context = "\n\n".join(
            f"[{i+1}] (type={d.source_type}, title={d.title or '-'}, source={d.source_url or '-'})\n{d.chunk_text}"
            for i, d in enumerate(docs)
        )
        completion = self.client.chat.completions.create(
            model="gpt-4.1-mini",
            temperature=0.1,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"질문: {question}\n\n근거:\n{context}"},
            ],
        )
        answer = completion.choices[0].message.content or "확인된 정보가 부족합니다."
        return answer, citations


ai_service = AIService()
