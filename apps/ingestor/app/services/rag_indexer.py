import json
from datetime import date, datetime
import math

from openai import OpenAI
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..models import Attachment, CalendarEvent, Meal, Notice, RagChunk, Source
from ..utils.text import split_chunks
from .attachment_text_extractor import extract_attachment_text


class RagIndexer:
    def __init__(self) -> None:
        self.client = OpenAI(api_key=settings.OPENAI_KEY) if settings.OPENAI_KEY else None

    def _embed(self, text_input: str) -> list[float] | None:
        if not self.client:
            return None
        emb = self.client.embeddings.create(model="text-embedding-3-small", input=text_input)
        return emb.data[0].embedding

    def _replace_chunks(
        self,
        db: Session,
        *,
        source_key: str,
        source_type: str,
        title: str | None,
        source_url: str | None,
        notice_id: int | None,
        text: str,
        extra: dict | None = None,
    ) -> int:
        def clean(value: str | None) -> str | None:
            if value is None:
                return None
            return value.replace("\x00", "")

        db.query(RagChunk).filter(RagChunk.source_key == source_key).delete()
        created = 0
        safe_text = clean(text) or ""
        safe_title = clean(title)
        safe_source_url = clean(source_url)
        safe_extra_json = clean(json.dumps(extra or {}, ensure_ascii=False))

        for idx, chunk in enumerate(split_chunks(safe_text)):
            db.add(
                RagChunk(
                    notice_id=notice_id,
                    source_url=safe_source_url,
                    source_type=source_type,
                    source_key=clean(source_key) or source_key,
                    chunk_index=idx,
                    title=safe_title,
                    extra_json=safe_extra_json,
                    chunk_text=clean(chunk) or "",
                    updated_at=datetime.utcnow(),
                )
            )
            created += 1
        return created

    def index_notices_incremental(self, db: Session, changed_notice_ids: list[int] | None = None) -> dict:
        stmt = select(Notice, Source.name).join(Source, Notice.source_id == Source.id)
        if changed_notice_ids is not None:
            if not changed_notice_ids:
                return {"notice_chunks": 0, "notice_docs": 0}
            stmt = stmt.where(Notice.id.in_(changed_notice_ids))
        else:
            db.query(RagChunk).filter(RagChunk.source_type == "notice_body").delete()
        rows = db.execute(stmt).all()
        docs = 0
        chunks = 0
        for notice, source_name in rows:
            text = "\n".join(
                [
                    f"[제목] {notice.title}",
                    f"[출처] {source_name}",
                    f"[게시일] {notice.published_at.isoformat() if notice.published_at else '-'}",
                    f"[본문] {notice.body_text or ''}",
                ]
            )
            source_key = f"notice:{notice.id}"
            chunks += self._replace_chunks(
                db,
                source_key=source_key,
                source_type="notice_body",
                title=notice.title,
                source_url=notice.link,
                notice_id=notice.id,
                text=text,
                extra={"published_at": notice.published_at.isoformat() if notice.published_at else None, "source": source_name},
            )
            docs += 1
        db.commit()
        return {"notice_chunks": chunks, "notice_docs": docs}

    def index_attachments_incremental(self, db: Session, changed_notice_ids: list[int] | None = None) -> dict:
        stmt = select(Attachment, Notice.title, Notice.link).join(Notice, Attachment.notice_id == Notice.id)
        if changed_notice_ids is not None:
            if not changed_notice_ids:
                return {"attachment_chunks": 0, "attachment_docs": 0}
            stmt = stmt.where(Attachment.notice_id.in_(changed_notice_ids))
        else:
            db.query(RagChunk).filter(RagChunk.source_type.in_(["attachment_text", "attachment_meta"])).delete()
        rows = db.execute(stmt).all()
        docs = 0
        chunks = 0
        for attachment, notice_title, notice_link in rows:
            source_key = f"attachment:{attachment.id}"
            text, meta = extract_attachment_text(attachment.local_path, filename_hint=attachment.filename)
            if text:
                chunks += self._replace_chunks(
                    db,
                    source_key=source_key,
                    source_type="attachment_text",
                    title=attachment.filename,
                    source_url=attachment.source_url,
                    notice_id=attachment.notice_id,
                    text=text,
                    extra={
                        "filename": attachment.filename,
                        "sha256": attachment.sha256,
                        "notice_title": notice_title,
                        "notice_url": notice_link,
                        "parse": meta,
                    },
                )
            else:
                meta_text = "\n".join(
                    [
                        f"[첨부파일] {attachment.filename}",
                        f"[공지 제목] {notice_title}",
                        f"[첨부 URL] {attachment.source_url}",
                        f"[파싱 상태] {meta.get('reason')}",
                    ]
                )
                chunks += self._replace_chunks(
                    db,
                    source_key=source_key,
                    source_type="attachment_meta",
                    title=attachment.filename,
                    source_url=attachment.source_url,
                    notice_id=attachment.notice_id,
                    text=meta_text,
                    extra={
                        "filename": attachment.filename,
                        "sha256": attachment.sha256,
                        "notice_title": notice_title,
                        "notice_url": notice_link,
                        "parse": meta,
                    },
                )
            docs += 1
        db.commit()
        return {"attachment_chunks": chunks, "attachment_docs": docs}

    def index_meals_incremental(self, db: Session, from_date: date | None = None) -> dict:
        stmt = select(Meal).order_by(Meal.meal_date.asc(), Meal.cafeteria_key.asc())
        if from_date:
            stmt = stmt.where(Meal.meal_date >= from_date)
        else:
            db.query(RagChunk).filter(RagChunk.source_type == "meal").delete()
        rows = db.scalars(stmt).all()
        grouped: dict[tuple[str, str], dict] = {}
        for row in rows:
            key = (row.meal_date.isoformat(), row.cafeteria_key)
            if key not in grouped:
                grouped[key] = {
                    "date": row.meal_date.isoformat(),
                    "cafeteria_key": row.cafeteria_key,
                    "cafeteria_name": row.cafeteria_name,
                    "breakfast": None,
                    "lunch": None,
                    "dinner": None,
                }
            grouped[key][row.meal_type] = row.menu

        docs = 0
        chunks = 0
        for item in grouped.values():
            text = "\n".join(
                [
                    f"[식당] {item['cafeteria_name']}",
                    f"[날짜] {item['date']}",
                    f"[조식] {item['breakfast'] or '-'}",
                    f"[중식] {item['lunch'] or '-'}",
                    f"[석식] {item['dinner'] or '-'}",
                ]
            )
            source_key = f"meal:{item['date']}:{item['cafeteria_key']}"
            chunks += self._replace_chunks(
                db,
                source_key=source_key,
                source_type="meal",
                title=f"{item['cafeteria_name']} {item['date']}",
                    source_url="https://www.pusan.ac.kr/kor/CMS/MenuMgr/menuListOnBuilding.do?mCode=MN202",
                notice_id=None,
                text=text,
                extra=item,
            )
            docs += 1
        db.commit()
        return {"meal_chunks": chunks, "meal_docs": docs}

    def index_calendar_incremental(self, db: Session, year: int | None = None) -> dict:
        stmt = select(CalendarEvent).order_by(CalendarEvent.start_date.asc(), CalendarEvent.id.asc())
        if year:
            start = date(year, 1, 1)
            end = date(year, 12, 31)
            stmt = stmt.where(CalendarEvent.start_date <= end, CalendarEvent.end_date >= start)
        else:
            db.query(RagChunk).filter(RagChunk.source_type == "calendar").delete()
        rows = db.scalars(stmt).all()
        docs = 0
        chunks = 0
        for ev in rows:
            text = "\n".join(
                [
                    f"[일정명] {ev.title}",
                    f"[분류] {ev.category}",
                    f"[기간] {ev.start_date.isoformat()} ~ {ev.end_date.isoformat()}",
                ]
            )
            source_key = f"calendar:{ev.id}"
            chunks += self._replace_chunks(
                db,
                source_key=source_key,
                source_type="calendar",
                title=ev.title,
                source_url=ev.source_url,
                notice_id=None,
                text=text,
                extra={
                    "category": ev.category,
                    "start_date": ev.start_date.isoformat(),
                    "end_date": ev.end_date.isoformat(),
                },
            )
            docs += 1
        db.commit()
        return {"calendar_chunks": chunks, "calendar_docs": docs}

    def refresh_missing_embeddings(self, db: Session, limit: int | None = None) -> int:
        if not self.client:
            return 0
        limit = limit or settings.RAG_EMBED_BATCH_LIMIT
        rows = db.query(RagChunk).filter(RagChunk.embedding.is_(None)).limit(limit).all()
        updated = 0
        for row in rows:
            try:
                row.embedding = self._embed(row.chunk_text)
                row.updated_at = datetime.utcnow()
                db.flush()
                updated += 1
            except Exception:
                db.rollback()
        db.commit()
        return updated

    def search_chunks(self, db: Session, question: str, top_k: int) -> list[RagChunk]:
        if top_k <= 0:
            return []
        vector = self._embed(question)
        if vector is None:
            return db.query(RagChunk).order_by(RagChunk.updated_at.desc(), RagChunk.id.desc()).limit(top_k).all()

        rows = db.query(RagChunk).filter(RagChunk.embedding.is_not(None)).limit(8000).all()
        scored: list[tuple[float, RagChunk]] = []
        for row in rows:
            emb = row.embedding
            if emb is None:
                continue
            dot = sum(x * y for x, y in zip(vector, emb))
            na = math.sqrt(sum(x * x for x in vector)) or 1.0
            nb = math.sqrt(sum(y * y for y in emb)) or 1.0
            dist = 1.0 - (dot / (na * nb))
            scored.append((dist, row))
        scored.sort(key=lambda x: x[0])
        top_rows = [r for _, r in scored[: max(top_k * 4, 24)]]

        # Source diversity rebalance.
        by_type: dict[str, list[RagChunk]] = {}
        for row in top_rows:
            by_type.setdefault(row.source_type or "unknown", []).append(row)

        picked: list[RagChunk] = []
        targets = [("notice_body", 3), ("attachment_text", 2), ("attachment_meta", 1), ("meal", 1), ("calendar", 1)]
        for source_type, count in targets:
            pool = by_type.get(source_type, [])
            picked.extend(pool[:count])

        if len(picked) < top_k:
            seen = {p.id for p in picked}
            for row in top_rows:
                if row.id in seen:
                    continue
                picked.append(row)
                if len(picked) >= top_k:
                    break

        return picked[:top_k]


rag_indexer = RagIndexer()
