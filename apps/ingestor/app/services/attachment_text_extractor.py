import csv
import io
import json
import re
import zipfile
from pathlib import Path

from bs4 import BeautifulSoup
from pypdf import PdfReader

from ..config import settings
from ..utils.text import normalize_whitespace


SUPPORTED_TEXT_EXTS = {".txt", ".md", ".csv", ".json", ".html", ".htm", ".pdf", ".docx"}
META_ONLY_EXTS = {".hwp", ".hwpx", ".zip", ".rar", ".7z"}


def _read_text_bytes(data: bytes) -> str:
    for enc in ("utf-8", "cp949", "euc-kr"):
        try:
            return data.decode(enc)
        except Exception:
            continue
    return data.decode("utf-8", errors="ignore")


def _sanitize_text(value: str) -> str:
    return value.replace("\x00", "")


def _extract_pdf_text(path: Path) -> str:
    reader = PdfReader(str(path))
    texts: list[str] = []
    for page in reader.pages:
        try:
            texts.append(page.extract_text() or "")
        except Exception:
            continue
    return "\n".join(texts)


def _extract_docx_text(path: Path) -> str:
    texts: list[str] = []
    with zipfile.ZipFile(path, "r") as zf:
        if "word/document.xml" not in zf.namelist():
            return ""
        xml = zf.read("word/document.xml").decode("utf-8", errors="ignore")
        # Minimal OOXML text extraction without extra heavy deps.
        raw = re.sub(r"</w:p>", "\n", xml)
        raw = re.sub(r"<[^>]+>", "", raw)
        texts.append(raw)
    return "\n".join(texts)


def extract_attachment_text(local_path: str, filename_hint: str | None = None) -> tuple[str | None, dict]:
    path = Path(local_path)
    ext = path.suffix.lower()
    if ext in {"", ".do", ".asp"} and filename_hint:
        hint_ext = Path(filename_hint).suffix.lower()
        if hint_ext:
            ext = hint_ext
    meta = {
        "ext": ext,
        "size_bytes": path.stat().st_size if path.exists() else 0,
        "supported": ext in SUPPORTED_TEXT_EXTS,
        "meta_only": ext in META_ONLY_EXTS,
        "parsed": False,
        "reason": None,
    }

    if not path.exists():
        meta["reason"] = "file_not_found"
        return None, meta

    if meta["size_bytes"] > settings.ATTACHMENT_PARSE_MAX_MB * 1024 * 1024:
        meta["reason"] = "file_too_large"
        return None, meta

    if ext in META_ONLY_EXTS:
        meta["reason"] = "meta_only_ext"
        return None, meta

    try:
        if ext in {".txt", ".md"}:
            text = _read_text_bytes(path.read_bytes())
        elif ext == ".csv":
            rows = []
            with io.StringIO(_read_text_bytes(path.read_bytes())) as f:
                reader = csv.reader(f)
                for row in reader:
                    rows.append(" | ".join(row))
            text = "\n".join(rows)
        elif ext == ".json":
            obj = json.loads(_read_text_bytes(path.read_bytes()))
            text = json.dumps(obj, ensure_ascii=False, indent=2)
        elif ext in {".html", ".htm"}:
            soup = BeautifulSoup(_read_text_bytes(path.read_bytes()), "lxml")
            text = soup.get_text("\n", strip=True)
        elif ext == ".pdf":
            text = _extract_pdf_text(path)
        elif ext == ".docx":
            text = _extract_docx_text(path)
        else:
            meta["reason"] = "unsupported_ext"
            return None, meta
    except Exception as exc:
        meta["reason"] = f"parse_error:{exc.__class__.__name__}"
        return None, meta

    normalized = normalize_whitespace(_sanitize_text(text))
    if not normalized:
        meta["reason"] = "empty_text"
        return None, meta

    meta["parsed"] = True
    return normalized, meta
