from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from ..config import settings
from ..db import SessionLocal
from ..models import SyncJob
from .sync_service import cleanup_stale_running_jobs, run_sync_job

scheduler = BackgroundScheduler(timezone="Asia/Seoul")


def _enqueue_all_sync() -> None:
    db = SessionLocal()
    try:
        job = SyncJob(target="all", status="queued")
        db.add(job)
        db.commit()
        db.refresh(job)
        run_sync_job(job.id, None, False)
    finally:
        db.close()


def _cleanup_stale_sync_jobs() -> None:
    db = SessionLocal()
    try:
        cleanup_stale_running_jobs(db, stale_minutes=settings.STALE_SYNC_MINUTES)
    finally:
        db.close()


def start_scheduler() -> None:
    if scheduler.running:
        return
    trigger = CronTrigger.from_crontab(settings.SYNC_CRON)
    scheduler.add_job(_enqueue_all_sync, trigger=trigger, id="periodic_sync", replace_existing=True)
    scheduler.add_job(
        _cleanup_stale_sync_jobs,
        trigger=IntervalTrigger(minutes=1),
        id="cleanup_stale_sync_jobs",
        replace_existing=True,
    )
    scheduler.start()


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
