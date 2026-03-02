import re


def normalize_source_url(url: str) -> str:
    cleaned = (url or "").strip()
    cleaned = re.sub(r"\s+", "", cleaned)
    return cleaned.replace("subvㅁiew.do", "subview.do")
