from collections import defaultdict
from datetime import date, datetime, time, timedelta
import json
from zoneinfo import ZoneInfo

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Attachment, CalendarEvent, Meal, Notice, NoticeImage, RagChunk, Source, SyncJob
from ..config import settings
from ..schemas import (
    DashboardSummary,
    DashboardTopNotice,
    AIQueryRequest,
    AIQueryResponse,
    RagReindexRequest,
    RagStatusResponse,
    CalendarEventItem,
    MealItem,
    NoticeDetail,
    NoticeListItem,
    SyncRunRequest,
    SyncRunResponse,
)
from ..services.ai_service import ai_service
from ..services.rag_indexer import rag_indexer
from ..services.sync_service import ensure_calendar_seeded, run_sync_job

router = APIRouter()
KST = ZoneInfo("Asia/Seoul")

SOURCE_DISPLAY_NAMES = {
    "cse_notice": "컴퓨터공학과",
    "grad_notice": "일반대학원",
    "go_grad_notice": "대학원 입학",
    "ai_notice": "AI 대학원",
    "aisec_notice": "융합보안대학원",
    "bk4_notice": "BK4-ICE 공지",
    "bk4_repo": "BK4-ICE 자료실",
}


@router.get("/health")
def health():
    return {"ok": True, "time": datetime.utcnow().isoformat()}


@router.get("/api/notices", response_model=list[NoticeListItem])
def list_notices(
    q: str | None = None,
    source: list[str] | None = Query(default=None),
    crawl_mode: str | None = None,
    from_date: str | None = Query(default=None, alias="from"),
    to_date: str | None = Query(default=None, alias="to"),
    hasAttachment: bool = False,
    hasImage: bool = False,
    sort: str = "recent",
    page: int = 1,
    page_size: int = 300,
    db: Session = Depends(get_db),
):
    stmt = select(Notice, Source.name, Source.crawl_mode).join(Source, Notice.source_id == Source.id)

    if q:
        stmt = stmt.where(or_(Notice.title.ilike(f"%{q}%"), Notice.body_text.ilike(f"%{q}%")))
    if source:
        stmt = stmt.where(Source.name.in_(source))
    if crawl_mode:
        stmt = stmt.where(Source.crawl_mode == crawl_mode)
    if from_date:
        stmt = stmt.where(Notice.published_at >= datetime.fromisoformat(from_date))
    if to_date:
        stmt = stmt.where(Notice.published_at <= datetime.fromisoformat(to_date))
    if hasAttachment:
        stmt = stmt.where(Notice.id.in_(select(Attachment.notice_id)))
    if hasImage:
        stmt = stmt.where(Notice.id.in_(select(NoticeImage.notice_id)))

    if sort == "popular":
        stmt = stmt.order_by(
            case((Notice.id.in_(select(Attachment.notice_id)), 1), else_=0).desc(),
            Notice.published_at.desc().nullslast(),
            Notice.id.desc(),
        )
    else:
        stmt = stmt.order_by(Notice.published_at.desc().nullslast(), Notice.id.desc())
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)

    rows = db.execute(stmt).all()
    notice_ids = [n.id for n, _, _ in rows]
    attachment_notice_ids = set()
    image_notice_ids = set()
    if notice_ids:
        attachment_notice_ids = set(db.scalars(select(Attachment.notice_id).where(Attachment.notice_id.in_(notice_ids))).all())
        image_notice_ids = set(db.scalars(select(NoticeImage.notice_id).where(NoticeImage.notice_id.in_(notice_ids))).all())
    return [
        NoticeListItem(
            id=n.id,
            source=source_name,
            source_display_name=SOURCE_DISPLAY_NAMES.get(source_name, source_name),
            crawl_mode=mode or "k2web_rss",
            title=n.title,
            link=n.link,
            author=n.author,
            published_at=n.published_at,
            has_attachment=n.id in attachment_notice_ids,
            has_image=n.id in image_notice_ids,
        )
        for n, source_name, mode in rows
    ]


@router.get("/api/notices/{notice_id}", response_model=NoticeDetail)
def get_notice(notice_id: int, db: Session = Depends(get_db)):
    row = db.execute(select(Notice, Source.name).join(Source, Notice.source_id == Source.id).where(Notice.id == notice_id)).first()
    if not row:
        raise HTTPException(status_code=404, detail="notice not found")
    notice, source_name = row

    attachments = db.scalars(select(Attachment).where(Attachment.notice_id == notice.id)).all()
    images = db.scalars(select(NoticeImage).where(NoticeImage.notice_id == notice.id)).all()

    return NoticeDetail(
        id=notice.id,
        source=source_name,
        title=notice.title,
        link=notice.link,
        author=notice.author,
        published_at=notice.published_at,
        body_html=notice.body_html,
        body_text=notice.body_text,
        images=[i.local_path for i in images],
        attachments=[
            {"filename": a.filename, "local_path": a.local_path, "source_url": a.source_url}
            for a in attachments
        ],
    )


@router.get("/api/meals", response_model=list[MealItem])
def get_meals(
    month: str,
    cafeteria: str | None = None,
    flat: bool = False,
    db: Session = Depends(get_db),
):
    stmt = select(Meal).where(func.to_char(Meal.meal_date, "YYYY-MM") == month)
    if cafeteria:
        stmt = stmt.where(Meal.cafeteria_key == cafeteria)
    rows = db.scalars(stmt.order_by(Meal.meal_date.asc(), Meal.cafeteria_name.asc())).all()

    if flat:
        grouped: dict = defaultdict(lambda: {"breakfast": None, "lunch": None, "dinner": None})
        for row in rows:
            grouped[row.meal_date][row.meal_type] = row.menu
        return [MealItem(date=d, **menus) for d, menus in sorted(grouped.items(), key=lambda x: x[0])]

    grouped: dict = defaultdict(lambda: {"breakfast": None, "lunch": None, "dinner": None, "cafeteria_key": None, "cafeteria_name": None})
    for row in rows:
        key = (row.meal_date, row.cafeteria_key)
        grouped[key][row.meal_type] = row.menu
        grouped[key]["cafeteria_key"] = row.cafeteria_key
        grouped[key]["cafeteria_name"] = row.cafeteria_name

    return [
        MealItem(date=d, cafeteria_key=ck, cafeteria_name=v["cafeteria_name"], breakfast=v["breakfast"], lunch=v["lunch"], dinner=v["dinner"])
        for (d, ck), v in sorted(grouped.items(), key=lambda x: (x[0][0], x[0][1]))
    ]


@router.get("/api/calendar", response_model=list[CalendarEventItem])
def get_calendar(year: int, db: Session = Depends(get_db)):
    ensure_calendar_seeded(db)
    start = datetime(year, 1, 1).date()
    end = datetime(year, 12, 31).date()

    rows = db.scalars(
        select(CalendarEvent).where(and_(CalendarEvent.start_date <= end, CalendarEvent.end_date >= start)).order_by(CalendarEvent.start_date.asc())
    ).all()

    return [
        CalendarEventItem(
            id=r.id,
            title=r.title,
            category=r.category,
            start_date=r.start_date,
            end_date=r.end_date,
            source_url=r.source_url,
        )
        for r in rows
    ]


@router.get("/api/dashboard/summary", response_model=DashboardSummary)
def dashboard_summary(db: Session = Depends(get_db)):
    today = datetime.now(KST).date()
    today_start = datetime.combine(today, time.min)
    tomorrow_start = today_start + timedelta(days=1)

    today_notice_count = db.scalar(
        select(func.count(Notice.id)).where(
            and_(Notice.published_at.is_not(None), Notice.published_at >= today_start, Notice.published_at < tomorrow_start)
        )
    ) or 0

    today_meal_rows = db.scalars(select(Meal).where(Meal.meal_date == today).order_by(Meal.cafeteria_name.asc())).all()
    by_cafeteria: dict[str, dict] = {}
    for row in today_meal_rows:
        if row.cafeteria_key not in by_cafeteria:
            by_cafeteria[row.cafeteria_key] = {
                "cafeteria_key": row.cafeteria_key,
                "cafeteria_name": row.cafeteria_name,
                "breakfast": None,
                "lunch": None,
                "dinner": None,
            }
        by_cafeteria[row.cafeteria_key][row.meal_type] = row.menu

    today_meals_by_cafeteria = list(by_cafeteria.values())
    today_meals = {"breakfast": None, "lunch": None, "dinner": None}
    if today_meals_by_cafeteria:
        today_meals = {
            "breakfast": today_meals_by_cafeteria[0].get("breakfast"),
            "lunch": today_meals_by_cafeteria[0].get("lunch"),
            "dinner": today_meals_by_cafeteria[0].get("dinner"),
        }

    top_candidates = db.execute(
        select(Notice, Source.name)
        .join(Source, Notice.source_id == Source.id)
        .order_by(Notice.published_at.desc().nullslast(), Notice.id.desc())
        .limit(50)
    ).all()
    candidate_ids = [n.id for n, _ in top_candidates]
    attached_ids = set()
    if candidate_ids:
        attached_ids = set(db.scalars(select(Attachment.notice_id).where(Attachment.notice_id.in_(candidate_ids))).all())
    top_notices = [
        DashboardTopNotice(
            id=n.id,
            title=n.title,
            source=source_name,
            published_at=n.published_at,
            has_attachment=n.id in attached_ids,
        )
        for n, source_name in top_candidates
    ]
    top_notices.sort(key=lambda x: (x.has_attachment, x.published_at or datetime.min), reverse=True)
    top_notices = top_notices[:8]

    source_rows = db.execute(
        select(Source.name, func.count(Notice.id))
        .outerjoin(Notice, Notice.source_id == Source.id)
        .where(Source.source_type == "notice", Source.active.is_(True))
        .group_by(Source.name)
        .order_by(Source.name.asc())
    ).all()
    source_stats = [
        {
            "source": name,
            "source_display_name": SOURCE_DISPLAY_NAMES.get(name, name),
            "count": int(count),
        }
        for name, count in source_rows
    ]

    last_job = db.scalar(select(SyncJob).order_by(SyncJob.updated_at.desc(), SyncJob.id.desc()).limit(1))
    last_progress = {}
    if last_job and last_job.progress_json:
        try:
            last_progress = json.loads(last_job.progress_json)
        except json.JSONDecodeError:
            last_progress = {}
    last_sync = {
        "job_id": last_job.id if last_job else None,
        "status": last_job.status if last_job else "unknown",
        "updated_at": last_job.updated_at.isoformat() if last_job and last_job.updated_at else None,
        "message": last_job.message if last_job else None,
        "current_source": last_progress.get("current_source"),
        "stage_current": last_progress.get("stage_current"),
        "progress_total_pages": last_progress.get("progress_total_pages", 0),
        "progress_done_pages": last_progress.get("progress_done_pages", 0),
        "stage_total": last_progress.get("stage_total", 0),
        "stage_done": last_progress.get("stage_done", 0),
    }

    return DashboardSummary(
        today_notice_count=int(today_notice_count),
        today_meals=today_meals,
        today_meals_by_cafeteria=today_meals_by_cafeteria,
        top_notices=top_notices,
        last_sync=last_sync,
        source_stats=source_stats,
    )


@router.post("/api/sync/run", response_model=SyncRunResponse)
def run_sync(req: SyncRunRequest, bg: BackgroundTasks, db: Session = Depends(get_db)):
    if req.target in ("notices", "all") and not req.backfill:
        cutoff = datetime.utcnow() - timedelta(hours=settings.NOTICE_SYNC_NOOP_HOURS)
        recent_done = db.scalar(
            select(SyncJob)
            .where(
                SyncJob.status == "completed",
                SyncJob.target.in_(["notices", "all"]),
                SyncJob.updated_at >= cutoff,
            )
            .order_by(SyncJob.updated_at.desc(), SyncJob.id.desc())
            .limit(1)
        )
        if recent_done:
            return SyncRunResponse(
                job_id=recent_done.id,
                status="noop",
                no_op=True,
                message=(
                    f"최근 {settings.NOTICE_SYNC_NOOP_HOURS}시간 내 완료된 notices 동기화가 있어 새 job을 생성하지 않았습니다. "
                    f"(last_job_id={recent_done.id})"
                ),
            )

    job = SyncJob(target=req.target, status="queued")
    db.add(job)
    db.commit()
    db.refresh(job)

    bg.add_task(run_sync_job, job.id, req.sources or None, req.backfill)
    return SyncRunResponse(job_id=job.id, status=job.status, no_op=False)


@router.get("/api/sync/status/{job_id}")
def sync_status(job_id: int, db: Session = Depends(get_db)):
    job = db.scalar(select(SyncJob).where(SyncJob.id == job_id))
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    progress = {}
    if job.progress_json:
        try:
            progress = json.loads(job.progress_json)
        except json.JSONDecodeError:
            progress = {}

    error_summary = {}
    if job.error_summary:
        try:
            error_summary = json.loads(job.error_summary)
        except json.JSONDecodeError:
            error_summary = {}

    return {
        "job_id": job.id,
        "target": job.target,
        "status": job.status,
        "message": job.message,
        "progress_total_pages": progress.get("progress_total_pages", 0),
        "progress_done_pages": progress.get("progress_done_pages", 0),
        "stage_total": progress.get("stage_total", 0),
        "stage_done": progress.get("stage_done", 0),
        "stage_current": progress.get("stage_current"),
        "current_source": progress.get("current_source"),
        "error_count": error_summary.get("error_count", 0),
        "stale_timeout_minutes": settings.STALE_SYNC_MINUTES,
        "last_heartbeat_at": job.updated_at,
        "created_at": job.created_at,
        "updated_at": job.updated_at,
    }


@router.post("/api/ai/query", response_model=AIQueryResponse)
def ai_query(req: AIQueryRequest, db: Session = Depends(get_db)):
    ai_service.refresh_missing_embeddings(db, limit=100)
    answer, citations = ai_service.answer(db, req.question, top_k=req.topK, use_attachments=req.useAttachments)
    return AIQueryResponse(answer=answer, citations=citations)


@router.post("/api/rag/reindex")
def rag_reindex(req: RagReindexRequest, db: Session = Depends(get_db)):
    output: dict = {}
    target = req.target

    if target in ("all", "notices"):
        output["notices"] = rag_indexer.index_notices_incremental(db, changed_notice_ids=req.notice_ids)
    if target in ("all", "attachments"):
        output["attachments"] = rag_indexer.index_attachments_incremental(db, changed_notice_ids=req.notice_ids)
    if target in ("all", "meals"):
        output["meals"] = rag_indexer.index_meals_incremental(db, from_date=req.from_date)
    if target in ("all", "calendar"):
        output["calendar"] = rag_indexer.index_calendar_incremental(db, year=req.year)

    output["embedded"] = rag_indexer.refresh_missing_embeddings(db, limit=settings.RAG_EMBED_BATCH_LIMIT)
    return {"ok": True, "target": target, "result": output}


@router.get("/api/rag/status", response_model=RagStatusResponse)
def rag_status(db: Session = Depends(get_db)):
    total = db.scalar(select(func.count(RagChunk.id))) or 0
    embedded = db.scalar(select(func.count(RagChunk.id)).where(RagChunk.embedding.is_not(None))) or 0
    rows = db.execute(
        select(RagChunk.source_type, func.count(RagChunk.id)).group_by(RagChunk.source_type).order_by(RagChunk.source_type.asc())
    ).all()
    latest = db.scalar(select(func.max(RagChunk.updated_at)))
    return RagStatusResponse(
        chunks_total=int(total),
        embedded_total=int(embedded),
        by_source_type={name or "unknown": int(cnt) for name, cnt in rows},
        latest_updated_at=latest,
    )
