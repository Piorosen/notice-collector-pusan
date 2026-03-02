from sqlalchemy import text

from .models import Base, Source
from .utils.url_normalize import normalize_source_url


NOTICE_SOURCES = [
    {
        "name": "cse_notice",
        "source_type": "notice",
        "base_url": "https://cse.pusan.ac.kr/cse/14659/subview.do",
        "rss_url": "https://cse.pusan.ac.kr/bbs/cse/2611/rssList.do?row=100",
        "crawl_mode": "k2web_rss",
    },
    {
        "name": "grad_notice",
        "source_type": "notice",
        "base_url": "https://graduate.pusan.ac.kr/grad/62341/subview.do",
        "rss_url": "https://graduate.pusan.ac.kr/bbs/grad/15644/rssList.do?row=100",
        "crawl_mode": "k2web_rss",
    },
    {
        "name": "go_grad_notice",
        "source_type": "notice",
        "base_url": "https://go.pusan.ac.kr/graduate/pages/index.asp?p=91&b=B_1_16",
        "rss_url": None,
        "crawl_mode": "go_board_html",
        "list_url_template": "https://go.pusan.ac.kr/graduate/pages/index.asp?p=91&b=B_1_16&nPage={page}",
        "detail_url_template": "https://go.pusan.ac.kr/graduate/pages/index.asp?p=91&b=B_1_16&bn={bn}&m=read&nPage={page}&ct=&con_cate_02=&f=ALL&s=",
        "encoding_hint": "euc-kr",
    },
    {
        "name": "ai_notice",
        "source_type": "notice",
        "base_url": "https://ai.pusan.ac.kr/ai/2907/subview.do",
        "rss_url": "https://ai.pusan.ac.kr/bbs/ai/204/rssList.do?row=100",
        "crawl_mode": "k2web_rss",
    },
    {
        "name": "aisec_notice",
        "source_type": "notice",
        "base_url": "https://aisec.pusan.ac.kr/?page_id=429",
        "rss_url": None,
        "crawl_mode": "mangboard_html",
        "list_url_template": "https://aisec.pusan.ac.kr/?page_id=429&mode=list&board_page={page}",
        "detail_url_template": "https://aisec.pusan.ac.kr/?page_id=429&vid={vid}",
        "encoding_hint": "utf-8",
    },
    {
        "name": "bk4_notice",
        "source_type": "notice",
        "base_url": "https://bk4-ice.pusan.ac.kr/bk4-ice/57409/subview.do",
        "rss_url": "https://bk4-ice.pusan.ac.kr/bbs/bk4-ice/14094/rssList.do?row=100",
        "crawl_mode": "k2web_rss",
    },
    {
        "name": "bk4_repo",
        "source_type": "notice",
        "base_url": "https://bk4-ice.pusan.ac.kr/bk4-ice/57410/subview.do",
        "rss_url": "https://bk4-ice.pusan.ac.kr/bbs/bk4-ice/14095/rssList.do?row=100",
        "crawl_mode": "k2web_rss",
    },
    {
        "name": "pnu_meal",
        "source_type": "meal",
        "base_url": "https://www.pusan.ac.kr/kor/CMS/MenuMgr/menuListOnBuilding.do?mCode=MN202",
        "rss_url": None,
        "crawl_mode": "meal_html",
    },
    {
        "name": "pnu_calendar",
        "source_type": "calendar",
        "base_url": "https://his.pusan.ac.kr/style-guide/19273/subview.do",
        "rss_url": None,
        "crawl_mode": "calendar_html",
    },
]


def ensure_schema_compat(db):
    statements = [
        "ALTER TABLE sources ADD COLUMN IF NOT EXISTS crawl_mode VARCHAR(40)",
        "ALTER TABLE sources ADD COLUMN IF NOT EXISTS list_url_template TEXT",
        "ALTER TABLE sources ADD COLUMN IF NOT EXISTS detail_url_template TEXT",
        "ALTER TABLE sources ADD COLUMN IF NOT EXISTS encoding_hint VARCHAR(40)",
        "ALTER TABLE sources ADD COLUMN IF NOT EXISTS normalized_url TEXT",
        "ALTER TABLE sync_jobs ADD COLUMN IF NOT EXISTS progress_json TEXT",
        "ALTER TABLE sync_jobs ADD COLUMN IF NOT EXISTS error_summary TEXT",
        "ALTER TABLE meals ADD COLUMN IF NOT EXISTS cafeteria_key VARCHAR(80) DEFAULT 'default'",
        "ALTER TABLE meals ADD COLUMN IF NOT EXISTS cafeteria_name VARCHAR(120) DEFAULT '기본 식당'",
        "CREATE INDEX IF NOT EXISTS idx_notices_source_published_at ON notices (source_id, published_at DESC)",
        "CREATE INDEX IF NOT EXISTS idx_sync_jobs_status_updated_at ON sync_jobs (status, updated_at)",
        "CREATE INDEX IF NOT EXISTS idx_meals_cafeteria_date ON meals (cafeteria_key, meal_date DESC)",
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_meals_date_cafeteria_type ON meals (meal_date, cafeteria_key, meal_type)",
        "ALTER TABLE rag_chunks ADD COLUMN IF NOT EXISTS source_type VARCHAR(40) DEFAULT 'notice_body'",
        "ALTER TABLE rag_chunks ADD COLUMN IF NOT EXISTS source_key VARCHAR(255) DEFAULT ''",
        "ALTER TABLE rag_chunks ADD COLUMN IF NOT EXISTS chunk_index INTEGER DEFAULT 0",
        "ALTER TABLE rag_chunks ADD COLUMN IF NOT EXISTS title TEXT",
        "ALTER TABLE rag_chunks ADD COLUMN IF NOT EXISTS extra_json TEXT",
        "ALTER TABLE rag_chunks ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT NOW()",
        "ALTER TABLE rag_chunks ALTER COLUMN source_url DROP NOT NULL",
        "UPDATE rag_chunks SET source_key = CONCAT('legacy:', id) WHERE source_key IS NULL OR source_key = ''",
        "UPDATE rag_chunks SET chunk_index = 0 WHERE chunk_index IS NULL",
        "CREATE INDEX IF NOT EXISTS idx_rag_source_type ON rag_chunks (source_type)",
        "CREATE INDEX IF NOT EXISTS idx_rag_source_key ON rag_chunks (source_key)",
        "CREATE INDEX IF NOT EXISTS idx_rag_updated_at ON rag_chunks (updated_at)",
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_rag_sourcekey_chunk ON rag_chunks (source_key, chunk_index)",
    ]
    for stmt in statements:
        db.execute(text(stmt))
    db.commit()


def init_db(db):
    Base.metadata.create_all(bind=db.get_bind())
    ensure_schema_compat(db)

    existing = {s.name for s in db.query(Source).all()}
    for item in NOTICE_SOURCES:
        normalized_url = normalize_source_url(item["base_url"])
        if item["name"] in existing:
            src = db.query(Source).filter(Source.name == item["name"]).first()
            if src:
                src.base_url = item["base_url"]
                src.rss_url = item.get("rss_url")
                src.crawl_mode = item.get("crawl_mode", "k2web_rss")
                src.list_url_template = item.get("list_url_template")
                src.detail_url_template = item.get("detail_url_template")
                src.encoding_hint = item.get("encoding_hint")
                src.normalized_url = normalized_url
                src.active = True
            continue
        db.add(
            Source(
                name=item["name"],
                source_type=item["source_type"],
                base_url=item["base_url"],
                rss_url=item.get("rss_url"),
                crawl_mode=item.get("crawl_mode", "k2web_rss"),
                list_url_template=item.get("list_url_template"),
                detail_url_template=item.get("detail_url_template"),
                encoding_hint=item.get("encoding_hint"),
                normalized_url=normalized_url,
                active=True,
            )
        )
    db.commit()
