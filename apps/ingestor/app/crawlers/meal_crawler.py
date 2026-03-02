from __future__ import annotations

import calendar
import re
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import httpx
from bs4 import BeautifulSoup
from dateutil import parser as dt_parser

from ..utils.text import normalize_whitespace

MEAL_URL = "https://www.pusan.ac.kr/kor/CMS/MenuMgr/menuListOnBuilding.do?mCode=MN202"

TARGET_CAFETERIAS: dict[str, dict[str, str]] = {
    "PG001": {"cafeteria_key": "geumjeong_staff", "cafeteria_name": "금정회관 교직원 식당", "building_gb": "R001"},
    "PG002": {"cafeteria_key": "geumjeong_student", "cafeteria_name": "금정회관 학생 식당", "building_gb": "R001"},
    "PM002": {"cafeteria_key": "munchang", "cafeteria_name": "문창회관 식당", "building_gb": "R002"},
    "PS001": {"cafeteria_key": "saetbeol", "cafeteria_name": "샛벌회관 식당", "building_gb": "R003"},
    "PH002": {"cafeteria_key": "student_hall", "cafeteria_name": "학생회관 학생 식당", "building_gb": "R004"},
}

DATE_RE = re.compile(r"\d{4}\.\d{2}\.\d{2}")
KST = ZoneInfo("Asia/Seoul")


def _month_start_end(month: str) -> tuple[date, date]:
    dt = datetime.strptime(month, "%Y-%m")
    _, last_day = calendar.monthrange(dt.year, dt.month)
    return date(dt.year, dt.month, 1), date(dt.year, dt.month, last_day)


def _iter_mondays_covering_month(month: str) -> list[date]:
    start, end = _month_start_end(month)
    first_monday = start - timedelta(days=start.weekday())
    mondays: list[date] = []
    current = first_monday
    while current <= end:
        mondays.append(current)
        current += timedelta(days=7)
    return mondays


def _extract_available_restaurants(html: str) -> dict[str, str]:
    soup = BeautifulSoup(html, "lxml")
    restaurants: dict[str, str] = {}
    for a in soup.select("#childTab a[onclick]"):
        onclick = a.get("onclick", "")
        m = re.search(r"goSearchMenu\(\s*'[^']*'\s*,\s*'[^']*'\s*,\s*'([^']*)'", onclick)
        if not m:
            continue
        code = m.group(1)
        name = normalize_whitespace(a.get_text(" ", strip=True))
        if code:
            restaurants[code] = name
    return restaurants


def _parse_menu_table(
    html: str,
    cafeteria_key: str,
    cafeteria_name: str,
    month: str,
) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    table = soup.select_one("table.menu-tbl.type-day")
    if not table:
        return []

    month_start, month_end = _month_start_end(month)

    date_headers = [normalize_whitespace(node.get_text(" ", strip=True)) for node in table.select("thead th .date")]
    dates: list[date] = []
    for raw in date_headers:
        m = DATE_RE.search(raw)
        if not m:
            continue
        try:
            dates.append(dt_parser.parse(m.group(0)).date())
        except Exception:
            continue
    if not dates:
        return []

    meal_type_map = {"조식": "breakfast", "중식": "lunch", "석식": "dinner"}
    items: list[dict] = []
    for row in table.select("tbody tr"):
        th = row.find("th")
        if not th:
            continue
        header = normalize_whitespace(th.get_text(" ", strip=True))
        row_type = None
        for k, v in meal_type_map.items():
            if k in header:
                row_type = v
                break
        if not row_type:
            continue

        tds = row.find_all("td")
        for idx, td in enumerate(tds):
            if idx >= len(dates):
                continue
            d = dates[idx]
            if d < month_start or d > month_end:
                continue

            lines: list[str] = []
            for li in td.select("li"):
                title = normalize_whitespace(li.select_one("h3").get_text(" ", strip=True)) if li.select_one("h3") else ""
                body = normalize_whitespace(li.select_one("p").get_text(" ", strip=True)) if li.select_one("p") else ""
                merged = " / ".join([x for x in [title, body] if x])
                if merged:
                    lines.append(merged)
            if not lines:
                text = normalize_whitespace(td.get_text(" ", strip=True))
                if text:
                    lines.append(text)
            if not lines:
                continue

            items.append(
                {
                    "meal_date": d,
                    "meal_type": row_type,
                    "menu": "\n".join(lines),
                    "cafeteria_key": cafeteria_key,
                    "cafeteria_name": cafeteria_name,
                }
            )
    return items


async def _fetch_restaurant_week(
    client: httpx.AsyncClient,
    restaurant_code: str,
    building_gb: str,
    menu_date: date,
) -> str:
    payload = {
        "campus_gb": "PUSAN",
        "building_gb": building_gb,
        "restaurant_code": restaurant_code,
        "menu_date": menu_date.isoformat(),
        "mobile_mode": "",
    }
    resp = await client.post(MEAL_URL, data=payload)
    resp.raise_for_status()
    return resp.text


async def fetch_monthly_meals(month: str | None = None) -> list[dict]:
    target_month = month or datetime.now(KST).strftime("%Y-%m")
    mondays = _iter_mondays_covering_month(target_month)
    dedup: dict[tuple[date, str, str], dict] = {}

    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        first_page = await client.get(MEAL_URL)
        first_page.raise_for_status()
        available = _extract_available_restaurants(first_page.text)

        for restaurant_code, meta in TARGET_CAFETERIAS.items():
            if restaurant_code not in available:
                continue
            for monday in mondays:
                html = await _fetch_restaurant_week(client, restaurant_code, meta["building_gb"], monday)
                rows = _parse_menu_table(
                    html=html,
                    cafeteria_key=meta["cafeteria_key"],
                    cafeteria_name=meta["cafeteria_name"],
                    month=target_month,
                )
                for row in rows:
                    key = (row["meal_date"], row["cafeteria_key"], row["meal_type"])
                    dedup[key] = row

    return sorted(dedup.values(), key=lambda x: (x["meal_date"], x["cafeteria_name"], x["meal_type"]))
