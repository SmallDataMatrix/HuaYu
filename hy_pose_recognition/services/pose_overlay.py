from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Callable

from hy_pose_recognition.core import settings
from hy_pose_recognition.services.landmarks import MEDIAPIPE_BONES, POSE_RENDER_IDS


ProgressCallback = Callable[[int, int], None]

_MODEL_PATH = settings.project_root / "data" / "models" / "pose_landmarker_full.task"

# Detection tuning for wide, multi-person gym footage where the training subjects
# sit at mid-distance. A direct full-frame pass frequently drops one of several
# players on any given frame, so we (1) sample the clip to discover how many real
# players are present, then (2) track each one independently on an upscaled crop of
# its own region — which survives the global detector collapsing onto someone else.
_DETECT_CONFIDENCE = 0.25      # detection / presence threshold (lenient for distant subjects)
_COARSE_NUM_POSES = 6          # poses requested from each full-frame pass
_MIN_PLAYER_HEIGHT = 0.13      # min normalised bbox height to count as a foreground player
_ROI_PAD = 0.45                # padding around a player bbox before cropping
_CROP_UPSCALE_TARGET = 720     # px; upscale the player crop for sharper landmarks

# Multi-player discovery + tracking.
_MAX_PLAYERS = 4               # hard ceiling; the real count is decided by discovery
_DISCOVERY_SAMPLES = 40        # frames sampled to learn how many players are present
_DISCOVERY_SUPPORT_FRAC = 0.30  # a player must appear in >= this fraction of sampled frames
_CLUSTER_RADIUS = 0.16         # normalised radius for grouping discovery detections
_MATCH_DISTANCE = 0.20         # max centre distance to associate a detection with a track

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

    def _make_options(num_poses: int) -> Any:
        return landmarker_cls.PoseLandmarkerOptions(
            base_options=landmarker_cls.BaseOptions(model_asset_path=str(_MODEL_PATH)),
            running_mode=landmarker_cls.RunningMode.IMAGE,
            num_poses=num_poses,
            min_pose_detection_confidence=_DETECT_CONFIDENCE,
            min_pose_presence_confidence=_DETECT_CONFIDENCE,
            min_tracking_confidence=_DETECT_CONFIDENCE,
        )

    with landmarker_cls.PoseLandmarker.create_from_options(_make_options(_COARSE_NUM_POSES)) as coarse_lm, \
         landmarker_cls.PoseLandmarker.create_from_options(_make_options(1)) as fine_lm:
        # Decide how many distinct players are present and seed a track for each.
        tracks = _discover_players(cv2, mp_module, coarse_lm, capture, max_frames, width, height)
        capture.set(cv2.CAP_PROP_POS_FRAMES, 0)

        for frame_index in range(max_frames):
            ok, frame = capture.read()
            if not ok:
                break
            if frame.shape[1] != width or frame.shape[0] != height:
                frame = cv2.resize(frame, (width, height), interpolation=cv2.INTER_AREA)

            timestamp_ms = round(frame_index / fps * 1000)
            players = _track_players(cv2, mp_module, coarse_lm, fine_lm, frame, tracks, width, height)

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


def _discover_players(
    cv2: Any, mp_module: Any, coarse_lm: Any, capture: Any,
    max_frames: int, width: int, height: int,
) -> list[dict[str, Any]]:
    """Sample the clip to decide how many real players exist and seed a track per player.

    A full-frame pass often misses one of several mid-distance players on any given
    frame, so we sample frames across the clip, group detections that land in the
    same region, and keep only groups that recur often enough — real players — while
    discarding fleeting bystanders (spectators, passers-by). Returns one track dict
    per player, ordered left-to-right so player ids stay stable across the run.
    """
    sample_count = min(_DISCOVERY_SAMPLES, max_frames)
    step = max(1, (max_frames - 1) / max(1, sample_count - 1)) if sample_count > 1 else 1
    indices = sorted({round(i * step) for i in range(sample_count)})

    clusters: list[dict[str, Any]] = []
    for frame_index in indices:
        capture.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
        ok, frame = capture.read()
        if not ok:
            continue
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        result = coarse_lm.detect(mp_module.Image(image_format=mp_module.ImageFormat.SRGB, data=rgb))
        for landmarks in result.pose_landmarks:
            keypoints = _landmarks_to_keypoints(landmarks)
            if _kp_height(keypoints) >= _MIN_PLAYER_HEIGHT:
                _accumulate_cluster(clusters, _kp_center(keypoints), _kp_height(keypoints))

    min_support = max(2, round(_DISCOVERY_SUPPORT_FRAC * max(1, len(indices))))
    strong = [c for c in clusters if c["count"] >= min_support]
    if not strong and clusters:  # never detect nothing: fall back to the most-seen region
        strong = [max(clusters, key=lambda c: c["count"])]
    strong.sort(key=lambda c: c["count"], reverse=True)

    selected: list[dict[str, Any]] = []
    for cluster in strong:
        center = (cluster["sum_x"] / cluster["count"], cluster["sum_y"] / cluster["count"])
        if any(math.hypot(center[0] - s["center"][0], center[1] - s["center"][1]) < _CLUSTER_RADIUS
               for s in selected):
            continue
        median_height = sorted(cluster["heights"])[len(cluster["heights"]) // 2]
        selected.append({"center": center, "height": median_height})
        if len(selected) == _MAX_PLAYERS:
            break

    selected.sort(key=lambda s: s["center"][0])  # left -> right keeps player ids deterministic
    return [_new_track(pid, s["center"], s["height"], width, height) for pid, s in enumerate(selected)]


def _accumulate_cluster(
    clusters: list[dict[str, Any]], center: tuple[float, float], player_height: float
) -> None:
    """Add a detection to the nearest existing region cluster, or start a new one."""
    for cluster in clusters:
        cx = cluster["sum_x"] / cluster["count"]
        cy = cluster["sum_y"] / cluster["count"]
        if math.hypot(center[0] - cx, center[1] - cy) < _CLUSTER_RADIUS:
            cluster["sum_x"] += center[0]
            cluster["sum_y"] += center[1]
            cluster["heights"].append(player_height)
            cluster["count"] += 1
            return
    clusters.append({"sum_x": center[0], "sum_y": center[1], "heights": [player_height], "count": 1})


def _new_track(
    player_id: int, center: tuple[float, float], player_height: float, width: int, frame_height: int
) -> dict[str, Any]:
    """Build a track seeded with a rough bbox; the first crop pass locks onto the body."""
    half_w = max(0.04, 0.28 * player_height)  # players are taller than they are wide
    half_h = max(0.06, 0.5 * player_height)
    bbox = (center[0] - half_w, center[1] - half_h, center[0] + half_w, center[1] + half_h)
    return {"id": player_id, "center": center, "roi": _roi_pixels(bbox, width, frame_height)}


def _track_players(
    cv2: Any, mp_module: Any, coarse_lm: Any, fine_lm: Any, frame: Any,
    tracks: list[dict[str, Any]], width: int, height: int,
) -> list[dict[str, Any]]:
    """Track each known player for one frame, returning a player dict per visible track.

    Each track is matched to the nearest fresh full-frame detection, then refined on
    an upscaled crop of its region. When the full-frame pass misses a player, the crop
    of its previous region still recovers the skeleton — so players are not dropped
    just because the global detector collapsed onto someone else.
    """
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    result = coarse_lm.detect(mp_module.Image(image_format=mp_module.ImageFormat.SRGB, data=rgb))
    candidates = [kp for kp in (_landmarks_to_keypoints(lm) for lm in result.pose_landmarks)
                  if _kp_height(kp) >= _MIN_PLAYER_HEIGHT]

    used: set[int] = set()
    players: list[dict[str, Any]] = []
    for track in tracks:
        match_idx = _nearest_candidate(candidates, used, track["center"])
        seed_roi = (_roi_pixels(_kp_bbox(candidates[match_idx]), width, height)
                    if match_idx is not None else track["roi"])
        refined = _detect_on_crop(cv2, mp_module, fine_lm, frame, seed_roi, width, height)

        if refined is not None and _kp_height(refined) >= _MIN_PLAYER_HEIGHT:
            chosen = refined
        elif match_idx is not None:
            chosen = candidates[match_idx]
        else:
            continue  # player not visible this frame; keep last region for re-acquisition

        if match_idx is not None:
            used.add(match_idx)
        track["center"] = _kp_center(chosen)
        track["roi"] = _roi_pixels(_kp_bbox(chosen), width, height)
        players.append(_make_player(chosen, track["id"]))

    players.sort(key=lambda player: player["player_id"])
    return players


def _nearest_candidate(
    candidates: list[list[dict[str, float]]], used: set[int], center: tuple[float, float]
) -> int | None:
    """Index of the closest unused candidate within the match radius, else None."""
    best_idx, best_dist = None, _MATCH_DISTANCE
    for idx, keypoints in enumerate(candidates):
        if idx in used:
            continue
        cx, cy = _kp_center(keypoints)
        dist = math.hypot(cx - center[0], cy - center[1])
        if dist < best_dist:
            best_idx, best_dist = idx, dist
    return best_idx


def _detect_on_crop(
    cv2: Any, mp_module: Any, fine_lm: Any, frame: Any, roi: tuple[int, int, int, int],
    width: int, height: int,
) -> list[dict[str, float]] | None:
    """Detect a single pose on an upscaled subject crop, mapped back to full-frame coords."""
    rx0, ry0, rx1, ry1 = roi
    crop_w, crop_h = rx1 - rx0, ry1 - ry0
    if crop_w < 16 or crop_h < 16:
        return None

    crop = frame[ry0:ry1, rx0:rx1]
    scale = _CROP_UPSCALE_TARGET / max(crop_w, crop_h)
    if scale > 1.0:
        crop = cv2.resize(crop, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)

    rgb = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
    result = fine_lm.detect(mp_module.Image(image_format=mp_module.ImageFormat.SRGB, data=rgb))
    if not result.pose_landmarks:
        return None

    return [
        {
            "id": idx,
            "x": _clip((rx0 + _clip(lm.x) * crop_w) / width),
            "y": _clip((ry0 + _clip(lm.y) * crop_h) / height),
            "visibility": round(float(lm.visibility), 4),
        }
        for idx, lm in enumerate(result.pose_landmarks[0])
    ]


def _landmarks_to_keypoints(landmarks: Any) -> list[dict[str, float]]:
    return [
        {"id": idx, "x": _clip(lm.x), "y": _clip(lm.y), "visibility": round(float(lm.visibility), 4)}
        for idx, lm in enumerate(landmarks)
    ]


def _make_player(keypoints: list[dict[str, float]], player_id: int = 0) -> dict[str, Any]:
    return {"player_id": player_id, "keypoints": keypoints, "angles": _compute_angles(keypoints)}


def _kp_bbox(keypoints: list[dict[str, float]]) -> tuple[float, float, float, float]:
    xs = [kp["x"] for kp in keypoints]
    ys = [kp["y"] for kp in keypoints]
    return min(xs), min(ys), max(xs), max(ys)


def _kp_center(keypoints: list[dict[str, float]]) -> tuple[float, float]:
    x0, y0, x1, y1 = _kp_bbox(keypoints)
    return (x0 + x1) / 2, (y0 + y1) / 2


def _kp_height(keypoints: list[dict[str, float]]) -> float:
    _, y0, _, y1 = _kp_bbox(keypoints)
    return y1 - y0


def _roi_pixels(
    bbox: tuple[float, float, float, float], width: int, height: int
) -> tuple[int, int, int, int]:
    x0, y0, x1, y1 = bbox
    bw, bh = x1 - x0, y1 - y0
    rx0 = max(0.0, x0 - _ROI_PAD * bw)
    rx1 = min(1.0, x1 + _ROI_PAD * bw)
    ry0 = max(0.0, y0 - _ROI_PAD * bh)
    ry1 = min(1.0, y1 + _ROI_PAD * bh)
    return int(rx0 * width), int(ry0 * height), int(rx1 * width), int(ry1 * height)


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
