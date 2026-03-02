import asyncio
import re
from datetime import datetime
from pathlib import Path
from typing import Callable
from urllib.parse import parse_qs, urlencode, urljoin, urlparse, urlunparse

import feedparser
import httpx
from bs4 import BeautifulSoup
from dateutil import parser as dt_parser
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..models import Attachment, Notice, NoticeImage, Source
from ..utils.files import ensure_dir, sha256_bytes
from ..utils.text import normalize_whitespace
from ..utils.url_normalize import normalize_source_url

ARTCL_ID_RE = re.compile(r"/(\d+)/artclView\.do")
GO_VIEW_ID_RE = re.compile(r"js_board_view\((\d+)\)")
AUDIO_VISUAL_FILE_RE = re.compile(r"\.(hwp|hwpx|pdf|doc|docx|xls|xlsx|ppt|pptx|zip|rar|7z|jpg|jpeg|png|gif)$", re.I)
GO_MAX_PAGES = 1
MANGBOARD_MAX_PAGES = 1


def _decode_response_body(content: bytes, encoding_hint: str | None) -> str:
    if encoding_hint:
        try:
            return content.decode(encoding_hint, errors="ignore")
        except LookupError:
            pass
    for enc in ("utf-8", "euc-kr", "cp949"):
        try:
            return content.decode(enc, errors="ignore")
        except Exception:
            continue
    return content.decode("utf-8", errors="ignore")


async def _http_get_with_retry(client: httpx.AsyncClient, url: str, retries: int = 3) -> httpx.Response:
    last_exc: Exception | None = None
    for i in range(retries):
        try:
            r = await client.get(url)
            r.raise_for_status()
            return r
        except Exception as exc:
            last_exc = exc
            await asyncio.sleep(min(2 ** i, 3))
    if last_exc:
        raise last_exc
    raise RuntimeError("http request failed")


async def _download_file(
    client: httpx.AsyncClient,
    sem: asyncio.Semaphore,
    url: str,
    out_dir: Path,
) -> tuple[str, str] | None:
    if not url.startswith("http"):
        return None

    try:
        async with sem:
            r = await _http_get_with_retry(client, url, retries=2)
            data = r.content
    except Exception:
        return None

    digest = sha256_bytes(data)
    ext = Path(urlparse(url).path).suffix or ".bin"
    out_file = out_dir / f"{digest}{ext}"
    if not out_file.exists():
        out_file.write_bytes(data)
    return str(out_file), digest


def _extract_external_id(link: str) -> str:
    m = ARTCL_ID_RE.search(link)
    if m:
        return m.group(1)
    return link.rstrip("/").split("/")[-1]


def _normalize_notice_link(link: str, source: Source) -> str:
    cleaned = (link or "").strip()
    if not cleaned:
        return cleaned
    if cleaned.startswith("http://") or cleaned.startswith("https://"):
        return cleaned
    base = source.base_url or source.rss_url or ""
    return urljoin(base, cleaned)


def _extract_attachment_candidates(soup: BeautifulSoup, page_url: str) -> list[tuple[str, str]]:
    items: list[tuple[str, str]] = []
    for a in soup.select("a[href]"):
        href = (a.get("href") or "").strip()
        name = normalize_whitespace(a.get_text(" ", strip=True)) or "attachment"
        if not href or href.startswith("javascript:"):
            continue
        full = urljoin(page_url, href)
        path = urlparse(full).path
        if "download.do" in href or AUDIO_VISUAL_FILE_RE.search(path):
            items.append((name, full))
    return list(dict.fromkeys(items))


def _parse_k2web_notice_page(html: str, page_url: str) -> tuple[str, str, list[tuple[str, str]], list[str]]:
    soup = BeautifulSoup(html, "lxml")

    body_node = soup.select_one("div.artclView")
    body_html = str(body_node) if body_node else ""
    body_text = normalize_whitespace(body_node.get_text(" ", strip=True) if body_node else "")

    attachment_items = _extract_attachment_candidates(soup.select_one("div.artclItem.viewForm") or soup, page_url)

    image_urls: list[str] = []
    for img in soup.select("div.artclView img[src]"):
        src = img.get("src")
        if src:
            image_urls.append(urljoin(page_url, src))
    image_urls = list(dict.fromkeys(image_urls))

    return body_html, body_text, attachment_items, image_urls


def _parse_go_list(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    rows = soup.select("table.tb_type1 tr")
    out: list[dict] = []

    for row in rows:
        cells = row.find_all("td")
        if len(cells) < 4:
            continue
        a = cells[1].find("a", href=True)
        if not a:
            continue
        href = a.get("href", "")
        m = GO_VIEW_ID_RE.search(href)
        if not m:
            continue
        bn = m.group(1)
        title = normalize_whitespace(a.get_text(" ", strip=True))
        date_raw = normalize_whitespace(cells[2].get_text(" ", strip=True))

        out.append({"bn": bn, "title": title, "date_raw": date_raw})

    return out


def _build_go_page_url(base: str, page: int) -> str:
    parsed = urlparse(base)
    q = parse_qs(parsed.query, keep_blank_values=True)
    q["nPage"] = [str(page)]
    new_query = urlencode({k: v[-1] for k, v in q.items()})
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, new_query, parsed.fragment))


def _parse_go_detail(html: str, page_url: str) -> tuple[str, str, list[tuple[str, str]], list[str], str | None]:
    soup = BeautifulSoup(html, "lxml")

    content = soup.select_one("div.bbsRead .subj")
    body_html = str(content) if content else ""
    body_text = normalize_whitespace(content.get_text(" ", strip=True) if content else "")

    attachment_items = _extract_attachment_candidates(content or soup, page_url)

    image_urls: list[str] = []
    if content:
        for img in content.select("img[src]"):
            src = img.get("src")
            if src:
                image_urls.append(urljoin(page_url, src))
    image_urls = list(dict.fromkeys(image_urls))

    date_cell = soup.select_one("table.tb_type2 tr:nth-of-type(2) td")
    date_raw = normalize_whitespace(date_cell.get_text(" ", strip=True)) if date_cell else None

    return body_html, body_text, attachment_items, image_urls, date_raw


def _parse_mangboard_list(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    rows = soup.select("#sub51_board_body tr")
    out: list[dict] = []
    for row in rows:
        a = row.select_one("td.text-left a[href]")
        if not a:
            continue
        href = a.get("href", "")
        parsed = urlparse(href)
        q = parse_qs(parsed.query)
        vid = (q.get("vid") or [None])[0]
        if not vid:
            continue

        tds = row.find_all("td")
        author = normalize_whitespace(tds[2].get_text(" ", strip=True)) if len(tds) >= 3 else None
        date_raw = normalize_whitespace(tds[3].get_text(" ", strip=True)) if len(tds) >= 4 else None

        out.append(
            {
                "vid": vid,
                "title": normalize_whitespace(a.get_text(" ", strip=True)),
                "author": author,
                "date_raw": date_raw,
                "link": href,
            }
        )
    return out


def _parse_mangboard_detail(html: str, page_url: str) -> tuple[str, str, list[tuple[str, str]], list[str], str | None, str | None]:
    soup = BeautifulSoup(html, "lxml")

    content = soup.select_one("tr#mb_sub51_tr_content td.content-box")
    body_html = str(content) if content else ""
    body_text = normalize_whitespace(content.get_text(" ", strip=True) if content else "")

    attachment_items = _extract_attachment_candidates(content or soup, page_url)

    image_urls: list[str] = []
    if content:
        for img in content.select("img[src]"):
            src = img.get("src")
            if src:
                image_urls.append(urljoin(page_url, src))
    image_urls = list(dict.fromkeys(image_urls))

    date_cell = soup.select_one("#mb_sub51_tr_title td span[style*='float:right']")
    author_cell = soup.select_one("#mb_sub51_tr_user_name td")
    date_raw = normalize_whitespace(date_cell.get_text(" ", strip=True)) if date_cell else None
    author = normalize_whitespace(author_cell.get_text(" ", strip=True)) if author_cell else None

    return body_html, body_text, attachment_items, image_urls, date_raw, author


def _parse_datetime(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        return dt_parser.parse(raw)
    except Exception:
        return None


async def _upsert_notice_with_details(
    db: Session,
    source: Source,
    ext_id: str,
    title: str,
    link: str,
    author: str | None,
    published_at: datetime | None,
    body_html: str,
    body_text: str,
    attach_items: list[tuple[str, str]],
    image_urls: list[str],
    client: httpx.AsyncClient,
    file_sem: asyncio.Semaphore,
    attachment_dir: Path,
    image_dir: Path,
) -> tuple[bool, int, int]:
    notice = db.scalar(select(Notice).where(Notice.source_id == source.id, Notice.external_id == ext_id))
    created = False

    if not notice:
        notice = Notice(
            source_id=source.id,
            external_id=ext_id,
            title=title,
            link=link,
            author=author,
            published_at=published_at,
        )
        db.add(notice)
        db.flush()
        created = True
    else:
        notice.title = title or notice.title
        notice.link = link
        notice.author = author or notice.author
        notice.published_at = published_at or notice.published_at

    notice.body_html = body_html
    notice.body_text = body_text
    notice.cached_at = datetime.utcnow()

    db.query(Attachment).filter(Attachment.notice_id == notice.id).delete()
    db.query(NoticeImage).filter(NoticeImage.notice_id == notice.id).delete()

    image_tasks = [_download_file(client, file_sem, img_url, image_dir) for img_url in image_urls]
    image_results = await asyncio.gather(*image_tasks, return_exceptions=True)
    for img_url, saved in zip(image_urls, image_results):
        if not saved or isinstance(saved, Exception):
            continue
        local_path, _ = saved
        db.add(NoticeImage(notice_id=notice.id, source_url=img_url, local_path=local_path))

    file_tasks = [_download_file(client, file_sem, url, attachment_dir) for _, url in attach_items]
    file_results = await asyncio.gather(*file_tasks, return_exceptions=True)
    attached_count = 0
    for (name, url), saved in zip(attach_items, file_results):
        if not saved or isinstance(saved, Exception):
            continue
        local_path, digest = saved
        db.add(
            Attachment(
                notice_id=notice.id,
                filename=name,
                source_url=url,
                local_path=local_path,
                sha256=digest,
            )
        )
        attached_count += 1

    db.commit()
    return created, attached_count, notice.id


def _notice_exists(db: Session, source_id: int, ext_id: str) -> bool:
    return db.scalar(
        select(Notice.id).where(Notice.source_id == source_id, Notice.external_id == ext_id).limit(1)
    ) is not None


async def _crawl_k2web_rss_source(
    db: Session,
    source: Source,
    client: httpx.AsyncClient,
    notice_sem: asyncio.Semaphore,
    file_sem: asyncio.Semaphore,
    attachment_dir: Path,
    image_dir: Path,
    progress_callback: Callable[[dict], None] | None = None,
) -> dict:
    out = {"inserted": 0, "updated": 0, "skipped": 0, "pages_done": 1, "error_count": 0, "changed_notice_ids": []}
    if not source.rss_url:
        return out

    try:
        feed_resp = await _http_get_with_retry(client, source.rss_url, retries=2)
        feed = feedparser.parse(feed_resp.content)
    except Exception:
        out["error_count"] += 1
        return out

    for entry in feed.entries:
        link = _normalize_notice_link(entry.get("link"), source)
        if not link:
            continue
        ext_id = _extract_external_id(link)
        title = entry.get("title", "(제목 없음)")
        author = entry.get("author")
        published_at = _parse_datetime(entry.get("published") or entry.get("pubDate"))

        if _notice_exists(db, source.id, ext_id):
            out["skipped"] += 1
            if progress_callback:
                progress_callback(out)
            continue

        try:
            async with notice_sem:
                r = await _http_get_with_retry(client, link, retries=2)
            html = _decode_response_body(r.content, source.encoding_hint)
            body_html, body_text, attach_items, image_urls = _parse_k2web_notice_page(html, str(r.url))
            created, _, changed_notice_id = await _upsert_notice_with_details(
                db,
                source,
                ext_id,
                title,
                link,
                author,
                published_at,
                body_html,
                body_text,
                attach_items,
                image_urls,
                client,
                file_sem,
                attachment_dir,
                image_dir,
            )
            out["inserted"] += 1 if created else 0
            out["updated"] += 0 if created else 1
            out["changed_notice_ids"].append(changed_notice_id)
        except Exception:
            out["error_count"] += 1
            db.rollback()
        if progress_callback:
            progress_callback(out)

    return out


async def _crawl_go_html_source(
    db: Session,
    source: Source,
    client: httpx.AsyncClient,
    notice_sem: asyncio.Semaphore,
    file_sem: asyncio.Semaphore,
    attachment_dir: Path,
    image_dir: Path,
    backfill: bool,
    progress_callback: Callable[[dict], None] | None = None,
) -> dict:
    out = {"inserted": 0, "updated": 0, "skipped": 0, "pages_done": 0, "pages_total": 0, "error_count": 0, "changed_notice_ids": []}
    max_pages = GO_MAX_PAGES
    first_ids_seen: set[str] = set()

    for page in range(1, max_pages + 1):
        out["pages_total"] = page
        list_url = _build_go_page_url(source.base_url, page)
        try:
            async with notice_sem:
                r = await _http_get_with_retry(client, list_url, retries=2)
            html = _decode_response_body(r.content, source.encoding_hint)
            rows = _parse_go_list(html)
        except Exception:
            out["error_count"] += 1
            continue

        if not rows:
            break

        first_id = rows[0]["bn"]
        if first_id in first_ids_seen:
            break
        first_ids_seen.add(first_id)

        out["pages_done"] += 1
        if progress_callback:
            progress_callback(out)

        for item in rows:
            bn = item["bn"]
            title = item["title"]
            published_at = _parse_datetime(item.get("date_raw"))
            detail_url = source.detail_url_template.format(bn=bn, page=page) if source.detail_url_template else list_url
            ext_id = f"go:{bn}"

            if _notice_exists(db, source.id, ext_id):
                out["skipped"] += 1
                continue

            try:
                async with notice_sem:
                    dr = await _http_get_with_retry(client, detail_url, retries=2)
                detail_html = _decode_response_body(dr.content, source.encoding_hint)
                body_html, body_text, attach_items, image_urls, detail_date_raw = _parse_go_detail(detail_html, str(dr.url))
                created, _, changed_notice_id = await _upsert_notice_with_details(
                    db,
                    source,
                    ext_id,
                    title,
                    str(dr.url),
                    None,
                    _parse_datetime(detail_date_raw) or published_at,
                    body_html,
                    body_text,
                    attach_items,
                    image_urls,
                    client,
                    file_sem,
                    attachment_dir,
                    image_dir,
                )
                out["inserted"] += 1 if created else 0
                out["updated"] += 0 if created else 1
                out["changed_notice_ids"].append(changed_notice_id)
            except Exception:
                out["error_count"] += 1
                db.rollback()
                if progress_callback:
                    progress_callback(out)

    return out


async def _crawl_mangboard_html_source(
    db: Session,
    source: Source,
    client: httpx.AsyncClient,
    notice_sem: asyncio.Semaphore,
    file_sem: asyncio.Semaphore,
    attachment_dir: Path,
    image_dir: Path,
    backfill: bool,
    progress_callback: Callable[[dict], None] | None = None,
) -> dict:
    out = {"inserted": 0, "updated": 0, "skipped": 0, "pages_done": 0, "pages_total": 0, "error_count": 0, "changed_notice_ids": []}
    max_pages = MANGBOARD_MAX_PAGES
    first_ids_seen: set[str] = set()

    for page in range(1, max_pages + 1):
        out["pages_total"] = page
        list_url = source.list_url_template.format(page=page) if source.list_url_template else source.base_url
        try:
            async with notice_sem:
                r = await _http_get_with_retry(client, list_url, retries=2)
            html = _decode_response_body(r.content, source.encoding_hint)
            rows = _parse_mangboard_list(html)
        except Exception:
            out["error_count"] += 1
            continue

        if not rows:
            break

        first_id = rows[0]["vid"]
        if first_id in first_ids_seen:
            break
        first_ids_seen.add(first_id)

        out["pages_done"] += 1
        if progress_callback:
            progress_callback(out)

        for item in rows:
            vid = item["vid"]
            detail_url = source.detail_url_template.format(vid=vid) if source.detail_url_template else item["link"]
            ext_id = f"aisec:{vid}"
            published_at = _parse_datetime(item.get("date_raw"))

            if _notice_exists(db, source.id, ext_id):
                out["skipped"] += 1
                continue

            try:
                async with notice_sem:
                    dr = await _http_get_with_retry(client, detail_url, retries=2)
                detail_html = _decode_response_body(dr.content, source.encoding_hint)
                body_html, body_text, attach_items, image_urls, detail_date_raw, detail_author = _parse_mangboard_detail(detail_html, str(dr.url))
                created, _, changed_notice_id = await _upsert_notice_with_details(
                    db,
                    source,
                    ext_id,
                    item["title"],
                    str(dr.url),
                    detail_author or item.get("author"),
                    _parse_datetime(detail_date_raw) or published_at,
                    body_html,
                    body_text,
                    attach_items,
                    image_urls,
                    client,
                    file_sem,
                    attachment_dir,
                    image_dir,
                )
                out["inserted"] += 1 if created else 0
                out["updated"] += 0 if created else 1
                out["changed_notice_ids"].append(changed_notice_id)
            except Exception:
                out["error_count"] += 1
                db.rollback()
                if progress_callback:
                    progress_callback(out)

    return out


async def sync_notices(
    db: Session,
    sources_filter: list[str] | None = None,
    backfill: bool = False,
    progress_callback: Callable[[dict], None] | None = None,
) -> dict:
    stmt = select(Source).where(Source.source_type == "notice", Source.active == True)
    if sources_filter:
        stmt = stmt.where(Source.name.in_(sources_filter))
    sources = db.scalars(stmt).all()

    if not sources:
        result = {
            "inserted": 0,
            "updated": 0,
            "error_count": 0,
            "sources_total": 0,
            "sources_done": 0,
            "progress_total_pages": 0,
            "progress_done_pages": 0,
            "source_results": {},
            "changed_notice_ids": [],
        }
        if progress_callback:
            progress_callback(result | {"current_source": None})
        return result

    notice_sem = asyncio.Semaphore(settings.CRAWL_CONCURRENCY)
    file_sem = asyncio.Semaphore(settings.DOWNLOAD_CONCURRENCY)

    attachment_dir = ensure_dir("/workspace/storage/attachments")
    image_dir = ensure_dir("/workspace/storage/images")

    aggregate = {
        "inserted": 0,
        "updated": 0,
        "skipped": 0,
        "error_count": 0,
        "sources_total": len(sources),
        "sources_done": 0,
        "progress_total_pages": 0,
        "progress_done_pages": 0,
        "source_results": {},
        "changed_notice_ids": [],
    }

    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        for source in sources:
            source.base_url = normalize_source_url(source.base_url)
            if source.normalized_url != source.base_url:
                source.normalized_url = source.base_url
                db.commit()

            source_result = {"inserted": 0, "updated": 0, "skipped": 0, "error_count": 0, "pages_done": 0, "pages_total": 0, "changed_notice_ids": []}
            try:
                def on_source_progress(partial: dict) -> None:
                    if progress_callback:
                        progress_callback(
                            {
                                **aggregate,
                                "current_source": source.name,
                                "progress_total_pages": aggregate["progress_total_pages"] + partial.get("pages_total", 0),
                                "progress_done_pages": aggregate["progress_done_pages"] + partial.get("pages_done", 0),
                                "error_count": aggregate["error_count"] + partial.get("error_count", 0),
                            }
                        )

                if source.crawl_mode == "go_board_html":
                    source_result = await _crawl_go_html_source(
                        db,
                        source,
                        client,
                        notice_sem,
                        file_sem,
                        attachment_dir,
                        image_dir,
                        backfill,
                        on_source_progress,
                    )
                elif source.crawl_mode == "mangboard_html":
                    source_result = await _crawl_mangboard_html_source(
                        db,
                        source,
                        client,
                        notice_sem,
                        file_sem,
                        attachment_dir,
                        image_dir,
                        backfill,
                        on_source_progress,
                    )
                else:
                    source_result = await _crawl_k2web_rss_source(
                        db,
                        source,
                        client,
                        notice_sem,
                        file_sem,
                        attachment_dir,
                        image_dir,
                        on_source_progress,
                    )
            except Exception:
                db.rollback()
                source_result["error_count"] = source_result.get("error_count", 0) + 1

            aggregate["inserted"] += source_result.get("inserted", 0)
            aggregate["updated"] += source_result.get("updated", 0)
            aggregate["skipped"] += source_result.get("skipped", 0)
            aggregate["error_count"] += source_result.get("error_count", 0)
            aggregate["sources_done"] += 1
            aggregate["progress_done_pages"] += source_result.get("pages_done", 0)
            aggregate["progress_total_pages"] += source_result.get("pages_total", source_result.get("pages_done", 0))
            aggregate["source_results"][source.name] = source_result
            aggregate["changed_notice_ids"].extend(source_result.get("changed_notice_ids", []))

            if progress_callback:
                progress_callback({
                    **aggregate,
                    "current_source": source.name,
                })

    if progress_callback:
        progress_callback({
            **aggregate,
            "current_source": None,
        })
    aggregate["changed_notice_ids"] = sorted(set(aggregate["changed_notice_ids"]))
    return aggregate
