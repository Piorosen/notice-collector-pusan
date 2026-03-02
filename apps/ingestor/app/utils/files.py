import hashlib
from pathlib import Path


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def ensure_dir(path: str | Path) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p
