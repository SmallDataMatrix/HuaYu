from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from hy_pose_recognition.core import settings


@dataclass
class AnalysisJob:
    job_id: str
    status: str
    filename: str
    video_path: Path
    created_at: datetime
    annotated_video_path: Path | None = None
    progress: int = 0
    duration_sec: float = settings.default_duration_sec
    fps: int = settings.default_fps
    frame_count: int = 0
    width: int = 1280
    height: int = 720
    error: str | None = None
    frames: list[dict[str, Any]] = field(default_factory=list)
    strokes: list[dict[str, Any]] = field(default_factory=list)
    landings: list[dict[str, Any]] = field(default_factory=list)
