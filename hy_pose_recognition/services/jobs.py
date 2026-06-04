from __future__ import annotations

from threading import Lock
from typing import Any

from hy_pose_recognition.models.domain import AnalysisJob


class JobStore:
    def __init__(self) -> None:
        self._jobs: dict[str, AnalysisJob] = {}
        self._lock = Lock()

    def add(self, job: AnalysisJob) -> None:
        with self._lock:
            self._jobs[job.job_id] = job

    def get(self, job_id: str) -> AnalysisJob | None:
        with self._lock:
            return self._jobs.get(job_id)

    def update(self, job_id: str, **changes: Any) -> AnalysisJob:
        with self._lock:
            job = self._jobs[job_id]
            for field, value in changes.items():
                setattr(job, field, value)
            return job


def serialize_job(job: AnalysisJob, include_frames: bool = False) -> dict[str, Any]:
    data: dict[str, Any] = {
        "job_id": job.job_id,
        "status": job.status,
        "filename": job.filename,
        "created_at": job.created_at.isoformat(),
        "progress": job.progress,
        "duration_sec": round(job.duration_sec, 3),
        "fps": job.fps,
        "frame_count": job.frame_count,
        "width": job.width,
        "height": job.height,
        "error": job.error,
        "video_url": f"/api/v1/media/{job.job_id}",
        "annotated_video_url": f"/api/v1/media/{job.job_id}/annotated" if job.annotated_video_path else None,
    }
    if include_frames:
        data["frames"] = job.frames
    return data


job_store = JobStore()
