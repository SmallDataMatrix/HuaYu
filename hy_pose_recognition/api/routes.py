from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, File, HTTPException, UploadFile, WebSocket
from fastapi.responses import FileResponse

from hy_pose_recognition.core import settings
from hy_pose_recognition.models import AnalysisJob, CompareRequest
from hy_pose_recognition.services.analysis import process_job
from hy_pose_recognition.services.comparison import frame_for, get_comparison_path, render_skeleton_png
from hy_pose_recognition.services.jobs import job_store, serialize_job
from hy_pose_recognition.services.storage import (
    cleanup_expired_files,
    ensure_data_dirs,
    ensure_supported_duration,
    validate_upload,
)


router = APIRouter()


def get_job_or_404(job_id: str) -> AnalysisJob:
    job = job_store.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.post("/upload")
async def upload_videos(background_tasks: BackgroundTasks, files: list[UploadFile] = File(...)) -> dict[str, object]:
    if not files:
        raise HTTPException(status_code=400, detail="At least one video file is required")
    if len(files) > 2:
        raise HTTPException(status_code=400, detail="Upload one video or two videos for comparison mode")

    cleanup_expired_files()
    ensure_data_dirs()

    created_jobs = []
    for file in files:
        extension = validate_upload(file)
        job_id = str(uuid4())
        stored_path = settings.upload_dir / f"{job_id}{extension}"
        with stored_path.open("wb") as output:
            while chunk := await file.read(1024 * 1024):
                output.write(chunk)
        try:
            ensure_supported_duration(stored_path)
        except ValueError as exc:
            stored_path.unlink(missing_ok=True)
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        job = AnalysisJob(
            job_id=job_id,
            status="uploaded",
            filename=file.filename or stored_path.name,
            video_path=stored_path,
            created_at=datetime.now(UTC),
        )
        job_store.add(job)
        background_tasks.add_task(process_job, job_id)
        created_jobs.append(serialize_job(job))

    return {
        "jobs": created_jobs,
        "job_id": created_jobs[0]["job_id"],
        "comparison_job_id": created_jobs[1]["job_id"] if len(created_jobs) == 2 else None,
    }


@router.get("/status/{job_id}")
def job_status(job_id: str) -> dict[str, object]:
    return serialize_job(get_job_or_404(job_id))


@router.get("/result/{job_id}")
def job_result(job_id: str, offset: int = 0, limit: int = 900) -> dict[str, object]:
    job = get_job_or_404(job_id)
    if job.status != "completed":
        raise HTTPException(status_code=409, detail=f"Job is {job.status}")

    offset = max(0, offset)
    limit = max(1, min(limit, 1800))
    payload = serialize_job(job)
    payload["frames"] = job.frames[offset : offset + limit]
    payload["offset"] = offset
    payload["limit"] = limit
    payload["total_frames"] = len(job.frames)
    return payload


@router.get("/strokes/{job_id}")
def stroke_events(job_id: str) -> dict[str, object]:
    job = get_job_or_404(job_id)
    return {"job_id": job_id, "strokes": job.strokes}


@router.get("/landings/{job_id}")
def landing_points(job_id: str) -> dict[str, object]:
    job = get_job_or_404(job_id)
    counts: dict[str, int] = {}
    in_bounds = 0
    for landing in job.landings:
        counts[landing["zone"]] = counts.get(landing["zone"], 0) + 1
        in_bounds += int(landing["in_bounds"])
    return {
        "job_id": job_id,
        "landings": job.landings,
        "stats": {
            "total_landings": len(job.landings),
            "in_bounds": in_bounds,
            "out": len(job.landings) - in_bounds,
            "zone_counts": counts,
        },
    }


@router.post("/compare")
def compare_strokes(payload: CompareRequest) -> dict[str, object]:
    first_job = get_job_or_404(payload.first_job_id)
    second_job = get_job_or_404(payload.second_job_id or payload.first_job_id)
    if first_job.status != "completed" or second_job.status != "completed":
        raise HTTPException(status_code=409, detail="Both jobs must be completed before comparison")

    first_frame = frame_for(first_job, payload.first_frame, "first")
    second_frame = frame_for(second_job, payload.second_frame, "last")
    comparison_id = str(uuid4())
    render_skeleton_png(comparison_id, first_job, first_frame, second_job, second_frame)
    return {
        "comparison_id": comparison_id,
        "image_url": f"/api/v1/compare/{comparison_id}.png",
        "first": {"job_id": first_job.job_id, "frame_index": first_frame["frame_index"]},
        "second": {"job_id": second_job.job_id, "frame_index": second_frame["frame_index"]},
    }


@router.get("/compare/{comparison_id}.png")
def comparison_image(comparison_id: str) -> FileResponse:
    path = get_comparison_path(comparison_id)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Comparison image not found")
    return FileResponse(path, media_type="image/png", filename=f"huayu-comparison-{comparison_id}.png")


@router.get("/media/{job_id}")
def media(job_id: str) -> FileResponse:
    job = get_job_or_404(job_id)
    if not job.video_path.exists():
        raise HTTPException(status_code=404, detail="Video file not found")
    return FileResponse(job.video_path, filename=job.filename)


@router.get("/media/{job_id}/annotated")
def annotated_media(job_id: str) -> FileResponse:
    job = get_job_or_404(job_id)
    if job.annotated_video_path is None or not job.annotated_video_path.exists():
        raise HTTPException(status_code=404, detail="Annotated video file not found")
    filename = f"annotated-{job.annotated_video_path.name}"
    return FileResponse(job.annotated_video_path, media_type="video/mp4", filename=filename)


@router.websocket("/progress/{job_id}")
async def progress_socket(websocket: WebSocket, job_id: str) -> None:
    await websocket.accept()
    try:
        while True:
            try:
                job = get_job_or_404(job_id)
            except HTTPException:
                await websocket.send_json({"status": "error", "progress": 100, "error": "Job not found"})
                return
            await websocket.send_json(serialize_job(job))
            if job.status in {"completed", "error"}:
                return
            await asyncio.sleep(0.25)
    finally:
        await websocket.close()
