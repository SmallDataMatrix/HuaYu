from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Callable

from hy_pose_recognition.core import settings
from hy_pose_recognition.services.landmarks import MEDIAPIPE_BONES, POSE_RENDER_IDS


ProgressCallback = Callable[[int, int], None]

_MODEL_PATH = settings.project_root / "data" / "models" / "pose_landmarker_full.task"

# BGR colours per player index (teal, orange, magenta, yellow-green)
_LINE_COLORS = [
    (30, 205, 190),
    (0, 130, 255),
    (255, 0, 200),
    (0, 230, 230),
]
_ACCENT_COLORS = [
    (255, 105, 40),
    (40, 200, 255),
    (200, 40, 255),
    (40, 255, 180),
]


def render_pose_overlay_video(
    job_id: str,
    video_path: Path,
    duration_sec: float,
    progress_callback: ProgressCallback | None = None,
) -> tuple[Path, list[dict[str, Any]], int, int, int]:
    """Detect body landmarks for all visible players and draw them onto an output video."""
    cv2, mp_module, landmarker_cls = _load_pose_dependencies()
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
    total_detected = 0

    options = landmarker_cls.PoseLandmarkerOptions(
        base_options=landmarker_cls.BaseOptions(model_asset_path=str(_MODEL_PATH)),
        running_mode=landmarker_cls.RunningMode.IMAGE,
        num_poses=4,
        min_pose_detection_confidence=0.3,
        min_pose_presence_confidence=0.3,
        min_tracking_confidence=0.3,
    )

    with landmarker_cls.PoseLandmarker.create_from_options(options) as landmarker:
        for frame_index in range(max_frames):
            ok, frame = capture.read()
            if not ok:
                break
            if frame.shape[1] != width or frame.shape[0] != height:
                frame = cv2.resize(frame, (width, height), interpolation=cv2.INTER_AREA)

            timestamp_ms = round(frame_index / fps * 1000)
            players = _detect_players(cv2, mp_module, landmarker, frame, timestamp_ms)

            if players:
                total_detected += 1
                _draw_all_poses(cv2, frame, players)

            writer.write(frame)
            frames.append(
                {
                    "job_id": job_id,
                    "frame_index": len(frames),
                    "timestamp_ms": timestamp_ms,
                    "players": players,
                    "shuttle": {"detected": False, "bounding_box": None, "center": None},
                }
            )

            if progress_callback and frame_index % 15 == 0:
                progress_callback(frame_index, max_frames)

    capture.release()
    writer.release()

    if not frames or total_detected == 0:
        output_path.unlink(missing_ok=True)
        raise ValueError("未能在视频中检测到人体姿态，请上传人物完整、光线清晰的视频。")

    return output_path, frames, fps, width, height


def _load_pose_dependencies() -> tuple[Any, Any, Any]:
    try:
        import cv2
        import mediapipe as mp
        from mediapipe.tasks import python as mp_tasks
        from mediapipe.tasks.python import vision as mp_vision
    except ImportError as exc:
        raise RuntimeError("需要安装 opencv-python 和 mediapipe 才能生成骨架叠加视频。") from exc
    if not _MODEL_PATH.exists():
        raise RuntimeError(
            f"未找到姿态检测模型文件：{_MODEL_PATH}\n"
            "请运行：curl -L 'https://storage.googleapis.com/mediapipe-models/"
            "pose_landmarker/pose_landmarker_full/float16/1/pose_landmarker_full.task'"
            f" -o {_MODEL_PATH}"
        )

    class _Landmarker:
        """Thin namespace combining tasks classes for cleaner call sites."""
        BaseOptions = mp_tasks.BaseOptions
        RunningMode = mp_vision.RunningMode
        PoseLandmarkerOptions = mp_vision.PoseLandmarkerOptions
        PoseLandmarker = mp_vision.PoseLandmarker

    return cv2, mp, _Landmarker


def _scaled_size(source_width: int, source_height: int) -> tuple[int, int]:
    if source_width <= settings.max_width:
        return source_width, source_height
    scale = settings.max_width / source_width
    return settings.max_width, max(1, round(source_height * scale))


def _open_video_writer(cv2: Any, output_path: Path, fps: int, width: int, height: int) -> Any:
    # avc1 (H.264) is required for browser playback via data URI; mp4v is not web-compatible
    for fourcc_tag in ("avc1", "mp4v"):
        fourcc = cv2.VideoWriter_fourcc(*fourcc_tag)
        writer = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))
        if writer.isOpened():
            return writer
    raise ValueError("无法创建骨架叠加输出视频。")


def _detect_players(
    cv2: Any, mp_module: Any, landmarker: Any, frame: Any, timestamp_ms: int
) -> list[dict[str, Any]]:
    """Return a list of player dicts, each with 'player_id', 'keypoints', and 'angles'."""
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    mp_image = mp_module.Image(image_format=mp_module.ImageFormat.SRGB, data=rgb)
    result = landmarker.detect(mp_image)

    players = []
    for landmarks in result.pose_landmarks:
        keypoints = [
            {
                "id": idx,
                "x": _clip(lm.x),
                "y": _clip(lm.y),
                "visibility": round(float(lm.visibility), 4),
            }
            for idx, lm in enumerate(landmarks)
        ]
        players.append(
            {
                "player_id": len(players),
                "keypoints": keypoints,
                "angles": _compute_angles(keypoints),
            }
        )
    return players


def _draw_all_poses(cv2: Any, frame: Any, players: list[dict[str, Any]]) -> None:
    h, w = frame.shape[:2]
    for player in players:
        pid = player["player_id"] % len(_LINE_COLORS)
        _draw_single_pose(cv2, frame, player["keypoints"], _LINE_COLORS[pid], _ACCENT_COLORS[pid], w, h)


def _draw_single_pose(
    cv2: Any,
    frame: Any,
    keypoints: list[dict[str, float]],
    line_color: tuple[int, int, int],
    accent_color: tuple[int, int, int],
    width: int,
    height: int,
) -> None:
    by_id = {kp["id"]: kp for kp in keypoints}
    joint_color = (245, 245, 245)

    for start, end in MEDIAPIPE_BONES:
        if start not in by_id or end not in by_id:
            continue
        cv2.line(frame, _px(by_id[start], width, height), _px(by_id[end], width, height),
                 line_color, 5, cv2.LINE_AA)

    for idx in POSE_RENDER_IDS:
        if idx not in by_id:
            continue
        center = _px(by_id[idx], width, height)
        color = accent_color if idx in {14, 16, 26, 28} else joint_color
        cv2.circle(frame, center, 7, (20, 30, 40), -1, cv2.LINE_AA)
        cv2.circle(frame, center, 5, color, -1, cv2.LINE_AA)


def _px(point: dict[str, float], width: int, height: int) -> tuple[int, int]:
    return round(point["x"] * width), round(point["y"] * height)


def _compute_angles(keypoints: list[dict[str, float]]) -> dict[str, float]:
    by_id = {kp["id"]: kp for kp in keypoints}
    try:
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
    except (KeyError, ZeroDivisionError):
        return {k: 0.0 for k in ("right_elbow", "left_elbow", "right_knee", "left_knee",
                                  "right_shoulder", "right_hip", "trunk_rotation")}


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
