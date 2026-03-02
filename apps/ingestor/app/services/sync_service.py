import asyncio
import json
from datetime import datetime, timedelta
from threading import Lock
from concurrent.futures import ThreadPoolExecutor, as_completed
from zoneinfo import ZoneInfo

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from ..crawlers.calendar_crawler import fetch_calendar_events
from ..crawlers.meal_crawler import fetch_monthly_meals
from ..crawlers.notice_crawler import sync_notices
from ..config import settings
from ..db import SessionLocal
from ..models import CalendarEvent, Meal, SyncJob
from .rag_indexer import rag_indexer

_JOB_PROGRESS_LOCK = Lock()
KST = ZoneInfo("Asia/Seoul")


def _load_json_or_default(value: str | None, default: dict) -> dict:
    if not value:
        return dict(default)
    try:
        obj = json.loads(value)
        return obj if isinstance(obj, dict) else dict(default)
    except json.JSONDecodeError:
        return dict(default)


def update_job_progress(db: Session, job: SyncJob, patch: dict | None = None, error_patch: dict | None = None) -> None:
    progress = _load_json_or_default(job.progress_json, {})
    if patch:
        progress.update(patch)
    job.progress_json = json.dumps(progress, ensure_ascii=False, default=str)

    errors = _load_json_or_default(job.error_summary, {})
    if error_patch:
        errors.update(error_patch)
    elif patch:
        if "error_count" in patch:
            errors["error_count"] = patch.get("error_count", 0)
        if "current_source" in patch:
            errors["current_source"] = patch.get("current_source")
    job.error_summary = json.dumps(errors, ensure_ascii=False, default=str)
    job.updated_at = datetime.utcnow()
    db.commit()


def update_job_progress_by_job_id(job_id: int, patch: dict | None = None, error_patch: dict | None = None) -> None:
    with _JOB_PROGRESS_LOCK:
        db = SessionLocal()
        try:
            job = db.scalar(select(SyncJob).where(SyncJob.id == job_id))
            if not job:
                return
            update_job_progress(db, job, patch=patch, error_patch=error_patch)
        finally:
            db.close()


def increment_job_error(job_id: int, current_source: str | None = None) -> None:
    with _JOB_PROGRESS_LOCK:
        db = SessionLocal()
        try:
            job = db.scalar(select(SyncJob).where(SyncJob.id == job_id))
            if not job:
                return
            errors = _load_json_or_default(job.error_summary, {})
            errors["error_count"] = int(errors.get("error_count", 0)) + 1
            if current_source:
                errors["current_source"] = current_source
            job.error_summary = json.dumps(errors, ensure_ascii=False, default=str)
            job.updated_at = datetime.utcnow()
            db.commit()
        finally:
            db.close()


def cleanup_stale_running_jobs(db: Session, stale_minutes: int | None = None) -> int:
    stale_minutes = stale_minutes or settings.STALE_SYNC_MINUTES
    cutoff = datetime.utcnow() - timedelta(minutes=stale_minutes)
    stale_jobs = db.scalars(
        select(SyncJob).where(SyncJob.status == "running", SyncJob.updated_at < cutoff)
    ).all()
    for job in stale_jobs:
        job.status = "failed"
        job.message = f"stale heartbeat timeout ({stale_minutes}m)"
        existing_errors = _load_json_or_default(job.error_summary, {})
        existing_errors.update({"timeout": True, "stale_minutes": stale_minutes})
        job.error_summary = json.dumps(existing_errors, ensure_ascii=False, default=str)
        job.updated_at = datetime.utcnow()
    if stale_jobs:
        db.commit()
    return len(stale_jobs)


def _sync_calendar(db: Session) -> dict:
    events = asyncio.run(fetch_calendar_events())
    db.execute(delete(CalendarEvent))
    for e in events:
        db.add(
            CalendarEvent(
                source_url=e["source_url"],
                title=e["title"],
                category=e["category"],
                start_date=e["start_date"],
                end_date=e["end_date"],
            )
        )
    db.commit()
    return {"events": len(events)}


def ensure_calendar_seeded(db: Session) -> dict:
    existing = db.scalar(select(func.count(CalendarEvent.id))) or 0
    if existing > 0:
        return {"seeded": False, "events": int(existing)}
    result = _sync_calendar(db)
    return {"seeded": True, **result}


def _sync_meals(db: Session) -> dict:
    month = datetime.now(KST).strftime("%Y-%m")
    meals = asyncio.run(fetch_monthly_meals(month))
    if meals:
        dates = {m["meal_date"] for m in meals}
        db.execute(delete(Meal).where(Meal.meal_date.in_(dates)))
        for m in meals:
            db.add(
                Meal(
                    meal_date=m["meal_date"],
                    meal_type=m["meal_type"],
                    menu=m["menu"],
                    campus="PNU",
                    cafeteria_key=m["cafeteria_key"],
                    cafeteria_name=m["cafeteria_name"],
                )
            )
    db.commit()
    return {"meals": len(meals)}


def _run_notices_task(job_id: int, sources: list[str] | None, backfill: bool) -> dict:
    db = SessionLocal()
    try:
        def update_progress(progress: dict) -> None:
            update_job_progress_by_job_id(job_id, patch=progress)

        sync_result = asyncio.run(
            sync_notices(
                db,
                sources_filter=sources,
                backfill=backfill,
                progress_callback=update_progress,
            )
        )
        changed_notice_ids = sync_result.get("changed_notice_ids", [])
        update_job_progress_by_job_id(job_id, patch={"stage_current": "notices 색인 중", "current_source": "rag_notices"})
        rag_result = {
            "notices": rag_indexer.index_notices_incremental(db, changed_notice_ids=changed_notice_ids),
            "attachments": rag_indexer.index_attachments_incremental(db, changed_notice_ids=changed_notice_ids),
            "embedded": rag_indexer.refresh_missing_embeddings(db, limit=settings.RAG_EMBED_BATCH_LIMIT),
        }
        return {"sync": sync_result, "rag": rag_result}
    finally:
        db.close()


def _run_meals_task(job_id: int) -> dict:
    db = SessionLocal()
    try:
        update_job_progress_by_job_id(job_id, patch={"current_source": "meals"})
        sync_result = _sync_meals(db)
        update_job_progress_by_job_id(job_id, patch={"stage_current": "meals 색인 중", "current_source": "rag_meals"})
        rag_result = {
            "meals": rag_indexer.index_meals_incremental(db, from_date=None),
            "embedded": rag_indexer.refresh_missing_embeddings(db, limit=settings.RAG_EMBED_BATCH_LIMIT),
        }
        return {"sync": sync_result, "rag": rag_result}
    finally:
        db.close()


def _run_calendar_task(job_id: int) -> dict:
    db = SessionLocal()
    try:
        update_job_progress_by_job_id(job_id, patch={"current_source": "calendar"})
        sync_result = _sync_calendar(db)
        update_job_progress_by_job_id(job_id, patch={"stage_current": "calendar 색인 중", "current_source": "rag_calendar"})
        rag_result = {
            "calendar": rag_indexer.index_calendar_incremental(db, year=datetime.now(KST).year),
            "embedded": rag_indexer.refresh_missing_embeddings(db, limit=settings.RAG_EMBED_BATCH_LIMIT),
        }
        return {"sync": sync_result, "rag": rag_result}
    finally:
        db.close()


def run_sync_job(job_id: int, sources: list[str] | None = None, backfill: bool = False) -> None:
    db = SessionLocal()
    try:
        job = db.scalar(select(SyncJob).where(SyncJob.id == job_id))
        if not job:
            return

        job.status = "running"
        db.commit()
        update_job_progress_by_job_id(
            job_id,
            patch={
                "current_source": None,
                "progress_total_pages": 0,
                "progress_done_pages": 0,
                "error_count": 0,
                "stage_total": 0,
                "stage_done": 0,
                "stage_current": None,
            },
        )

        try:
            output = {}
            if job.target == "all":
                tasks = {
                    "notices": (_run_notices_task, (job_id, sources, backfill)),
                    "meals": (_run_meals_task, (job_id,)),
                    "calendar": (_run_calendar_task, (job_id,)),
                }
                stage_total = len(tasks)
                stage_done = 0
                update_job_progress_by_job_id(
                    job_id,
                    patch={"stage_total": stage_total, "stage_done": 0, "stage_current": "병렬 동기화 시작"},
                )

                with ThreadPoolExecutor(max_workers=3) as executor:
                    future_map = {
                        executor.submit(func, *args): name for name, (func, args) in tasks.items()
                    }
                    for future in as_completed(future_map):
                        name = future_map[future]
                        try:
                            output[name] = future.result()
                        except Exception as exc:
                            output[name] = {"error": str(exc)}
                            increment_job_error(job_id, current_source=name)
                        stage_done += 1
                        update_job_progress_by_job_id(
                            job_id,
                            patch={
                                "stage_total": stage_total,
                                "stage_done": stage_done,
                                "stage_current": f"{name} 완료",
                                "current_source": None if stage_done == stage_total else name,
                            },
                        )
            else:
                stage_total = 1
                update_job_progress_by_job_id(
                    job_id,
                    patch={
                        "stage_total": stage_total,
                        "stage_done": 0,
                        "stage_current": job.target,
                        "current_source": job.target,
                    },
                )
                if job.target == "notices":
                    output["notices"] = _run_notices_task(job_id, sources, backfill)
                if job.target == "meals":
                    output["meals"] = _run_meals_task(job_id)
                if job.target == "calendar":
                    output["calendar"] = _run_calendar_task(job_id)
                update_job_progress_by_job_id(
                    job_id,
                    patch={"stage_total": stage_total, "stage_done": stage_total, "stage_current": "완료", "current_source": None},
                )

            job.status = "completed"
            job.message = str(output)
        except Exception as exc:
            job.status = "failed"
            job.message = str(exc)

        job.updated_at = datetime.utcnow()
        db.commit()
    finally:
        db.close()


def cleanup_stale_running_jobs_with_new_session(stale_minutes: int | None = None) -> int:
    db = SessionLocal()
    try:
        return cleanup_stale_running_jobs(db, stale_minutes=stale_minutes)
    finally:
        db.close()
