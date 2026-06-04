from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Settings:
    app_title: str = "华羽AI羽毛球训练分析"
    version: str = "0.1.0"
    max_upload_seconds: int = 30
    max_width: int = 1920
    default_fps: int = 30
    default_duration_sec: float = 8.0
    retention_hours: int = 24
    project_root: Path = PROJECT_ROOT
    data_dir: Path = PROJECT_ROOT / "data"
    upload_dir: Path = PROJECT_ROOT / "data" / "uploads"
    processed_dir: Path = PROJECT_ROOT / "data" / "processed"
    comparison_dir: Path = PROJECT_ROOT / "data" / "comparisons"
    allowed_extensions: frozenset[str] = field(
        default_factory=lambda: frozenset({".mp4", ".mov", ".avi"})
    )


settings = Settings()
