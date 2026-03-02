from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.routes import router
from .bootstrap import init_db
from .config import settings
from .db import SessionLocal
from .services.scheduler import start_scheduler, stop_scheduler
from .services.sync_service import cleanup_stale_running_jobs

app = FastAPI(title="automatic-notice-ingestor", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup() -> None:
    db = SessionLocal()
    try:
        init_db(db)
        cleanup_stale_running_jobs(db, stale_minutes=settings.STALE_SYNC_MINUTES)
    finally:
        db.close()
    start_scheduler()


@app.on_event("shutdown")
def shutdown() -> None:
    stop_scheduler()


app.include_router(router)
