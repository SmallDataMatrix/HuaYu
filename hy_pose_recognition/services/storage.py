from __future__ import annotations

import json
import shutil
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from fastapi import UploadFile

from hy_pose_recognition.core import settings


def ensure_data_dirs() -> None:
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    settings.processed_dir.mkdir(parents=True, exist_ok=True)
    settings.comparison_dir.mkdir(parents=True, exist_ok=True)


def cleanup_expired_files() -> None:
    ensure_data_dirs()
    cutoff = datetime.now(UTC) - timedelta(hours=settings.retention_hours)
    if not settings.data_dir.exists():
        return
    for path in settings.data_dir.rglob("*"):
        if not path.is_file():
            continue
        modified_at = datetime.fromtimestamp(path.stat().st_mtime, UTC)
        if modified_at < cutoff:
            path.unlink(missing_ok=True)


def validate_upload(file: Any) -> str:
    extension = Path(file.filename or "").suffix.lower()
    if extension not in settings.allowed_extensions:
        formats = ", ".join(sorted(settings.allowed_extensions))
        raise ValueError(f"Unsupported video format. Use {formats}.")
    return extension


def video_duration_error(duration_sec: float) -> str:
    return (
        f"视频时长为 {duration_sec:.1f} 秒；"
        f"受当前计算能力限制，最多支持 {settings.max_upload_seconds} 秒。"
    )


def ensure_supported_duration(video_path: Path) -> tuple[float, int, int]:
    duration_sec, width, height = probe_video(video_path)
    if duration_sec > settings.max_upload_seconds:
        raise ValueError(video_duration_error(duration_sec))
    return duration_sec, width, height


def probe_video(video_path: Path) -> tuple[float, int, int]:
    ffprobe = shutil.which("ffprobe")
    if ffprobe is None:
        return settings.default_duration_sec, 1280, 720

    command = [
        ffprobe,
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=width,height,duration",
        "-of",
        "json",
        str(video_path),
    ]
    try:
        completed = subprocess.run(command, capture_output=True, check=True, text=True, timeout=8)
        payload = json.loads(completed.stdout or "{}")
        stream = (payload.get("streams") or [{}])[0]
        duration = float(stream.get("duration") or settings.default_duration_sec)
        width = int(stream.get("width") or 1280)
        height = int(stream.get("height") or 720)
    except (OSError, subprocess.SubprocessError, ValueError, KeyError, IndexError, json.JSONDecodeError):
        return settings.default_duration_sec, 1280, 720

    return max(0.1, duration), width, height
