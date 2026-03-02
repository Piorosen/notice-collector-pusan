import re
from datetime import date, datetime

import httpx
from bs4 import BeautifulSoup

from ..utils.text import normalize_whitespace

CALENDAR_URL = "https://his.pusan.ac.kr/style-guide/19273/subview.do"
DATE_RANGE_RE = re.compile(
    r"(?P<s>\d{4}[./-]\d{1,2}[./-]\d{1,2})(?:\s*~\s*(?P<e>\d{4}[./-]\d{1,2}[./-]\d{1,2}))?"
)

CATEGORY_KEYWORDS = {
    "enroll": ["수강", "수강신청", "수강정정"],
    "leave": ["휴학", "복학"],
    "registration": ["등록", "등록금"],
    "exam": ["시험", "중간", "기말"],
    "grade": ["성적"],
    "graduation": ["졸업", "학위"],
}


def _parse_date(text: str) -> date:
    for fmt in ("%Y.%m.%d", "%Y-%m-%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"invalid date: {text}")


def parse_date_range(raw: str) -> tuple[date, date]:
    cleaned = normalize_whitespace(raw)
    m = DATE_RANGE_RE.search(cleaned)
    if not m:
        raise ValueError(f"unable to parse date range: {raw}")

    start = _parse_date(m.group("s"))
    end_raw = m.group("e")
    end = _parse_date(end_raw) if end_raw else start
    return start, end


def categorize_event(title: str) -> str:
    t = normalize_whitespace(title)
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(k in t for k in keywords):
            return category
    return "general"


def parse_calendar_html(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    rows = soup.select("table.artclTable tbody tr")

    events: list[dict] = []
    for row in rows:
        cells = row.find_all("td")
        if len(cells) < 2:
            continue
        period = normalize_whitespace(cells[0].get_text(" ", strip=True))
        title = normalize_whitespace(cells[1].get_text(" ", strip=True))
        if not period or not title:
            continue

        try:
            start_date, end_date = parse_date_range(period)
        except ValueError:
            continue

        events.append(
            {
                "source_url": CALENDAR_URL,
                "title": title,
                "category": categorize_event(title),
                "start_date": start_date,
                "end_date": end_date,
            }
        )

    return events


async def fetch_calendar_events() -> list[dict]:
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        r = await client.get(CALENDAR_URL)
        r.raise_for_status()
        return parse_calendar_html(r.text)
