from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from hy_pose_recognition.core import settings
from hy_pose_recognition.models import AnalysisJob
from hy_pose_recognition.services.analysis import process_job
from hy_pose_recognition.services.jobs import job_store
from hy_pose_recognition.services.storage import (
    cleanup_expired_files,
    ensure_data_dirs,
    ensure_supported_duration,
)


def create_job_from_upload(filename: str, payload: bytes) -> AnalysisJob:
    ensure_data_dirs()
    cleanup_expired_files()

    suffix = Path(filename).suffix.lower() or ".mp4"
    job_id = str(uuid4())
    stored_path = settings.upload_dir / f"{job_id}{suffix}"
    stored_path.write_bytes(payload)
    try:
        ensure_supported_duration(stored_path)
    except ValueError:
        stored_path.unlink(missing_ok=True)
        raise

    job = AnalysisJob(
        job_id=job_id,
        status="uploaded",
        filename=filename,
        video_path=stored_path,
        created_at=datetime.now(UTC),
    )
    job_store.add(job)
    process_job(job_id)

    completed = job_store.get(job_id)
    if completed is None:
        raise RuntimeError("Analysis job disappeared before completion")
    return completed
