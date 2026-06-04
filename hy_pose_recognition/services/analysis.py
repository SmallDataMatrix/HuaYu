from __future__ import annotations

import math
import random
from uuid import uuid4

from hy_pose_recognition.services.jobs import job_store
from hy_pose_recognition.services.pose_overlay import render_pose_overlay_video
from hy_pose_recognition.services.storage import ensure_supported_duration


def build_strokes_from_motion(job_id: str, frames: list[dict[str, object]], fps: int) -> list[dict[str, object]]:
    if len(frames) < 30:
        return []

    # Wrist (id 16) speed per frame. Frames where the subject is not detected
    # (e.g. the coach briefly leaving the frame) have no keypoint; treat those as
    # zero motion so they are never picked as a contact and never crash the loop.
    speeds = []
    previous = _keypoint(frames[0], 16)
    for frame in frames[1:]:
        current = _keypoint(frame, 16)
        if current is None or previous is None:
            speeds.append(0.0)
            if current is not None:
                previous = current
            continue
        speeds.append(math.hypot(current["x"] - previous["x"], current["y"] - previous["y"]))
        previous = current

    ranked = sorted(enumerate(speeds, start=1), key=lambda item: item[1], reverse=True)
    selected: list[int] = []
    min_gap = max(8, round(fps * 0.55))
    for frame_index, speed in ranked:
        if speed <= 0:
            continue
        if all(abs(frame_index - other) >= min_gap for other in selected):
            selected.append(frame_index)
        if len(selected) == 3:
            break

    contacts = sorted(selected) or [
        max(12, min(len(frames) - 13, int(len(frames) * ratio)))
        for ratio in (0.22, 0.5, 0.78)
        if len(frames) > 30
    ]
    return [
        {
            "stroke_id": str(uuid4()),
            "job_id": job_id,
            "timestamp_ms": frames[contact]["timestamp_ms"],
            "type": "unknown",
            "confidence": 0.68,
            "keyframes": {
                "preparation": max(0, contact - round(fps * 0.35)),
                "contact": contact,
                "follow_through": min(len(frames) - 1, contact + round(fps * 0.4)),
            },
        }
        for contact in contacts
    ]


def _keypoint(frame: dict[str, object], keypoint_id: int) -> dict[str, float] | None:
    """Return the requested keypoint of the primary player, or None if absent."""
    players = frame.get("players", [])
    if not players:
        return None
    keypoints = players[0]["keypoints"]
    return next((item for item in keypoints if item["id"] == keypoint_id), None)


def landing_zone(x: float, y: float) -> str:
    vertical = "front" if y < 0.33 else "mid" if y < 0.66 else "rear"
    horizontal = "left" if x < 0.5 else "right"
    return f"{vertical}_{horizontal}"


def build_landings(job_id: str, strokes: list[dict[str, object]], seed: int) -> list[dict[str, object]]:
    rng = random.Random(seed)
    landings = []
    for index, stroke in enumerate(strokes):
        x = 0.22 + 0.62 * rng.random()
        y = 0.18 + 0.7 * rng.random()
        in_bounds = 0.06 <= x <= 0.94 and 0.05 <= y <= 0.95
        timestamp_ms = int(stroke["timestamp_ms"]) + 750
        landings.append(
            {
                "id": str(uuid4()),
                "job_id": job_id,
                "timestamp_ms": timestamp_ms,
                "court_coord": {"x": round(x, 3), "y": round(y, 3)},
                "in_bounds": in_bounds,
                "zone": landing_zone(x, y),
                "source": "synthetic",
                "stroke_index": index,
            }
        )
    return landings


def process_job(job_id: str) -> None:
    try:
        job = job_store.get(job_id)
        if job is None:
            return

        job_store.update(job_id, status="processing", progress=3)
        duration_sec, width, height = ensure_supported_duration(job.video_path)
        annotated_video_path, frames, fps, width, height = render_pose_overlay_video(
            job_id,
            job.video_path,
            duration_sec,
            progress_callback=lambda index, total: job_store.update(
                job_id,
                progress=min(92, 5 + round(index / max(total, 1) * 87)),
            ),
        )
        frame_count = len(frames)
        seed = sum(ord(char) for char in job_id)
        strokes = build_strokes_from_motion(job_id, frames, fps)

        job_store.update(
            job_id,
            annotated_video_path=annotated_video_path,
            duration_sec=duration_sec,
            fps=fps,
            frame_count=frame_count,
            width=width,
            height=height,
            frames=frames,
            strokes=strokes,
            landings=build_landings(job_id, strokes, seed),
            progress=100,
            status="completed",
        )
    except Exception as exc:  # pragma: no cover - defensive runtime guard.
        job_store.update(job_id, status="error", error=str(exc), progress=100)
