from datetime import date, datetime
from pydantic import BaseModel


class NoticeListItem(BaseModel):
    id: int
    source: str
    source_display_name: str
    crawl_mode: str
    title: str
    link: str
    author: str | None
    published_at: datetime | None
    has_attachment: bool
    has_image: bool


class NoticeDetail(BaseModel):
    id: int
    source: str
    title: str
    link: str
    author: str | None
    published_at: datetime | None
    body_html: str | None
    body_text: str | None
    images: list[str]
    attachments: list[dict]


class MealItem(BaseModel):
    date: date
    cafeteria_key: str | None = None
    cafeteria_name: str | None = None
    breakfast: str | None = None
    lunch: str | None = None
    dinner: str | None = None


class CalendarEventItem(BaseModel):
    id: int
    title: str
    category: str
    start_date: date
    end_date: date
    source_url: str


class SyncRunRequest(BaseModel):
    target: str = "all"
    full: bool = False
    sources: list[str] | None = None
    backfill: bool = False


class SyncRunResponse(BaseModel):
    job_id: int | None = None
    status: str
    no_op: bool = False
    message: str | None = None


class AIQueryRequest(BaseModel):
    question: str
    topK: int = 6
    useAttachments: bool = True


class AICitation(BaseModel):
    source_url: str | None = None
    source_type: str | None = None
    title: str | None = None
    source_key: str | None = None


class AIQueryResponse(BaseModel):
    answer: str
    citations: list[AICitation]


class RagReindexRequest(BaseModel):
    target: str = "all"  # all|notices|attachments|meals|calendar
    year: int | None = None
    from_date: date | None = None
    notice_ids: list[int] | None = None


class RagStatusResponse(BaseModel):
    chunks_total: int
    embedded_total: int
    by_source_type: dict
    latest_updated_at: datetime | None = None


class DashboardTopNotice(BaseModel):
    id: int
    title: str
    source: str
    published_at: datetime | None
    has_attachment: bool


class DashboardSummary(BaseModel):
    today_notice_count: int
    today_meals: dict
    today_meals_by_cafeteria: list[dict] = []
    top_notices: list[DashboardTopNotice]
    last_sync: dict
    source_stats: list[dict]
