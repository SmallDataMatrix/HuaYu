"""
Disk persistence for racket search results.

Layout under DATA_DIR/searches/:
  {slug}.json  — full payload: meta + records + videos + voc
  index.json   — lightweight index (meta only) for fast sidebar listing

All write operations are best-effort: failures are logged and swallowed so
session-state caching still works when the filesystem is read-only (e.g.
Streamlit Cloud container restart).
"""
import hashlib
import json
import logging
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path

_log = logging.getLogger(__name__)

from config import DATA_DIR

_SEARCHES_DIR = Path(DATA_DIR) / "searches"


def _norm_key(name: str) -> str:
    """Normalize racket name for dedup (mirrors bilibili._normalize)."""
    return re.sub(r"[\s\-_·•·【】《》「」『』]", "", name).lower()


def _slug(name: str) -> str:
    return hashlib.md5(_norm_key(name).encode()).hexdigest()[:12]


def _ensure_dir() -> bool:
    """Create the searches directory; return False if it can't be created."""
    try:
        _SEARCHES_DIR.mkdir(parents=True, exist_ok=True)
        return True
    except OSError as e:
        _log.warning("Cannot create searches dir %s: %s", _SEARCHES_DIR, e)
        return False


def _index_path() -> Path:
    return _SEARCHES_DIR / "index.json"


def _search_path(slug: str) -> Path:
    return _SEARCHES_DIR / f"{slug}.json"


def _read_index() -> dict:
    try:
        return json.loads(_index_path().read_text(encoding="utf-8"))
    except Exception:
        return {}


def _write_atomic(path: Path, data: dict) -> None:
    """Write JSON atomically via a temp file in the same dir."""
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


# ── Public API ────────────────────────────────────────────────────────────────

def save_search(
    racket_name: str,
    records: list[dict],
    videos: list[dict],
    voc: dict,
    *,
    logged_in: bool = False,
) -> dict:
    """Persist search result; return the meta dict. Writes are best-effort."""
    slug = _slug(racket_name)
    meta = {
        "name": racket_name,
        "slug": slug,
        "saved_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "n_videos": len(videos),
        "n_records": len(records),
        "summary": voc.get("summary", ""),
        "mode": "logged_in" if logged_in else "anonymous",
    }
    if not _ensure_dir():
        return meta
    payload = {"meta": meta, "records": records, "videos": videos, "voc": voc}
    try:
        _write_atomic(_search_path(slug), payload)
    except Exception as e:
        _log.warning("Could not write search %s: %s", slug, e)
        return meta
    try:
        index = _read_index()
        index[slug] = meta
        _write_atomic(_index_path(), index)
    except Exception as e:
        _log.warning("Could not update index: %s", e)
    return meta


def load_search(racket_name: str) -> dict | None:
    """Return {meta, records, videos, voc} or None if not found / corrupt."""
    path = _search_path(_slug(racket_name))
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def list_searches() -> list[dict]:
    """Return index entries sorted newest-first."""
    index = _read_index()
    return sorted(index.values(), key=lambda m: m.get("saved_at", ""), reverse=True)


def delete_search(racket_name: str) -> None:
    """Remove the search file and its index entry."""
    slug = _slug(racket_name)
    try:
        _search_path(slug).unlink(missing_ok=True)
    except Exception:
        pass
    index = _read_index()
    if slug in index:
        index.pop(slug)
        try:
            _write_atomic(_index_path(), index)
        except Exception:
            pass
