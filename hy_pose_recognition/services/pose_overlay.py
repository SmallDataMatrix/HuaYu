from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Callable

from hy_pose_recognition.core import settings
from hy_pose_recognition.services.landmarks import MEDIAPIPE_BONES, POSE_RENDER_IDS


ProgressCallback = Callable[[int, int], None]


def render_pose_overlay_video(
    job_id: str,
    video_path: Path,
    duration_sec: float,
    progress_callback: ProgressCallback | None = None,
) -> tuple[Path, list[dict[str, Any]], int, int, int]:
    """Detect real body landmarks and draw them onto an output video."""
    cv2, mp_pose = _load_pose_dependencies()
    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        raise ValueError("无法打开上传视频。")

    source_fps = capture.get(cv2.CAP_PROP_FPS) or settings.default_fps
    fps = int(round(source_fps)) if source_fps > 1 else settings.default_fps
    source_width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH) or 1280)
    source_height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT) or 720)
    width, height = _scaled_size(source_width, source_height)
    max_frames = max(1, min(int(duration_sec * fps), settings.max_upload_seconds * fps))

    output_path = settings.processed_dir / f"{job_id}.mp4"
    writer = _open_video_writer(cv2, output_path, fps, width, height)
    frames: list[dict[str, Any]] = []
    previous_keypoints: list[dict[str, float]] | None = None
    detected_count = 0

    with mp_pose.Pose(
        model_complexity=1,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5,
    ) as pose:
        for frame_index in range(max_frames):
            ok, frame = capture.read()
            if not ok:
                break
            if frame.shape[1] != width or frame.shape[0] != height:
                frame = cv2.resize(frame, (width, height), interpolation=cv2.INTER_AREA)

            keypoints = _detect_keypoints(cv2, pose, frame)
            detected = keypoints is not None
            if detected:
                previous_keypoints = keypoints
                detected_count += 1
            elif previous_keypoints is not None:
                keypoints = previous_keypoints
            else:
                writer.write(frame)
                if progress_callback and frame_index % 15 == 0:
                    progress_callback(frame_index, max_frames)
                continue

            _draw_pose(cv2, frame, keypoints, detected)
            frames.append(
                {
                    "job_id": job_id,
                    "frame_index": len(frames),
                    "timestamp_ms": round(len(frames) / fps * 1000),
                    "skeleton": {
                        "keypoints": keypoints,
                        "angles": _compute_angles(keypoints),
                        "detected": detected,
                    },
                    "shuttle": {"detected": False, "bounding_box": None, "center": None},
                }
            )
            writer.write(frame)

            if progress_callback and frame_index % 15 == 0:
                progress_callback(frame_index, max_frames)

    capture.release()
    writer.release()

    if not frames or detected_count == 0:
        output_path.unlink(missing_ok=True)
        raise ValueError("未能在视频中检测到人体姿态，请上传人物完整、光线清晰的视频。")

    return output_path, frames, fps, width, height


def _load_pose_dependencies() -> tuple[Any, Any]:
    try:
        import cv2
        import mediapipe as mp
    except ImportError as exc:  # pragma: no cover - depends on runtime environment.
        raise RuntimeError("需要安装 opencv-python 和 mediapipe 才能生成真实骨架叠加视频。") from exc
    return cv2, mp.solutions.pose


def _scaled_size(source_width: int, source_height: int) -> tuple[int, int]:
    if source_width <= settings.max_width:
        return source_width, source_height
    scale = settings.max_width / source_width
    return settings.max_width, max(1, round(source_height * scale))


def _open_video_writer(cv2: Any, output_path: Path, fps: int, width: int, height: int) -> Any:
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))
    if not writer.isOpened():
        raise ValueError("无法创建骨架叠加输出视频。")
    return writer


def _detect_keypoints(cv2: Any, pose: Any, frame: Any) -> list[dict[str, float]] | None:
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    rgb.flags.writeable = False
    result = pose.process(rgb)
    if not result.pose_landmarks:
        return None
    keypoints = []
    for index, landmark in enumerate(result.pose_landmarks.landmark):
        keypoints.append(
            {
                "id": index,
                "x": _clip(landmark.x),
                "y": _clip(landmark.y),
                "visibility": round(float(landmark.visibility), 4),
            }
        )
    return keypoints


def _draw_pose(cv2: Any, frame: Any, keypoints: list[dict[str, float]], detected: bool) -> None:
    height, width = frame.shape[:2]
    by_id = {item["id"]: item for item in keypoints}
    line_color = (30, 205, 190) if detected else (145, 160, 165)
    joint_color = (245, 245, 245) if detected else (145, 160, 165)
    accent_color = (40, 105, 255)

    for start, end in MEDIAPIPE_BONES:
        if start not in by_id or end not in by_id:
            continue
        start_xy = _pixel_xy(by_id[start], width, height)
        end_xy = _pixel_xy(by_id[end], width, height)
        cv2.line(frame, start_xy, end_xy, line_color, 5, cv2.LINE_AA)

    for index in POSE_RENDER_IDS:
        if index not in by_id:
            continue
        center = _pixel_xy(by_id[index], width, height)
        color = accent_color if index in {14, 16, 26, 28} else joint_color
        cv2.circle(frame, center, 7, (20, 30, 40), -1, cv2.LINE_AA)
        cv2.circle(frame, center, 5, color, -1, cv2.LINE_AA)


def _pixel_xy(point: dict[str, float], width: int, height: int) -> tuple[int, int]:
    return round(point["x"] * width), round(point["y"] * height)


def _compute_angles(keypoints: list[dict[str, float]]) -> dict[str, float]:
    by_id = {item["id"]: item for item in keypoints}
    shoulder_line = _segment_angle(by_id[11], by_id[12])
    hip_line = _segment_angle(by_id[23], by_id[24])
    trunk_rotation = abs(shoulder_line - hip_line)
    if trunk_rotation > 180:
        trunk_rotation = 360 - trunk_rotation

    return {
        "right_elbow": _angle_between(by_id[12], by_id[14], by_id[16]),
        "left_elbow": _angle_between(by_id[11], by_id[13], by_id[15]),
        "right_knee": _angle_between(by_id[24], by_id[26], by_id[28]),
        "left_knee": _angle_between(by_id[23], by_id[25], by_id[27]),
        "right_shoulder": _angle_between(by_id[24], by_id[12], by_id[14]),
        "right_hip": _angle_between(by_id[12], by_id[24], by_id[26]),
        "trunk_rotation": round(trunk_rotation, 1),
    }


def _angle_between(a: dict[str, float], b: dict[str, float], c: dict[str, float]) -> float:
    ba = (a["x"] - b["x"], a["y"] - b["y"])
    bc = (c["x"] - b["x"], c["y"] - b["y"])
    dot = ba[0] * bc[0] + ba[1] * bc[1]
    mag_ba = math.hypot(*ba)
    mag_bc = math.hypot(*bc)
    if mag_ba == 0 or mag_bc == 0:
        return 0.0
    cosine = max(-1.0, min(1.0, dot / (mag_ba * mag_bc)))
    return round(math.degrees(math.acos(cosine)), 1)


def _segment_angle(a: dict[str, float], b: dict[str, float]) -> float:
    return math.degrees(math.atan2(b["y"] - a["y"], b["x"] - a["x"]))


def _clip(value: float) -> float:
    return round(max(0.0, min(1.0, float(value))), 4)
