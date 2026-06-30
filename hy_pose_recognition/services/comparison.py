from __future__ import annotations

from pathlib import Path
from typing import Any

from hy_pose_recognition.core import settings
from hy_pose_recognition.models.domain import AnalysisJob
from hy_pose_recognition.services.landmarks import MEDIAPIPE_BONES, POSE_RENDER_IDS
from hy_pose_recognition.services.storage import ensure_data_dirs
from hy_pose_recognition.web.fonts import load_chinese_font

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:  # pragma: no cover - handled at runtime by compare endpoint.
    Image = None
    ImageDraw = None
    ImageFont = None


COMPARISONS: dict[str, Path] = {}


def frame_for(job: AnalysisJob, frame_index: int | None, fallback: str) -> dict[str, Any]:
    if not job.frames:
        raise ValueError(f"任务 {job.job_id} 没有已完成的帧数据")

    if frame_index is None:
        stroke = job.strokes[0] if fallback == "first" else job.strokes[-1]
        frame_index = stroke["keyframes"]["contact"]

    frame_index = max(0, min(frame_index, len(job.frames) - 1))
    return job.frames[frame_index]


def get_comparison_path(comparison_id: str) -> Path:
    return COMPARISONS.get(comparison_id) or settings.comparison_dir / f"{comparison_id}.png"


def register_comparison(comparison_id: str, path: Path) -> None:
    COMPARISONS[comparison_id] = path


def render_skeleton_png(
    comparison_id: str,
    first_job: AnalysisJob,
    first_frame: dict[str, Any],
    second_job: AnalysisJob,
    second_frame: dict[str, Any],
) -> Path:
    if Image is None or ImageDraw is None:
        raise RuntimeError("生成对比图片需要安装Pillow")

    ensure_data_dirs()
    width, height = 1440, 840
    image = Image.new("RGB", (width, height), "#f7f2e8")
    draw = ImageDraw.Draw(image)
    font = load_chinese_font(20) if ImageFont else None
    title_font = load_chinese_font(26) if ImageFont else None
    panel_fill = "#fffaf1"
    accent = "#e24d2e"
    bone_color = "#168a8a"
    joint_color = "#0b3b52"

    panels = [(60, 86, 690, 760), (750, 86, 1380, 760)]
    titles = [
        f"{first_job.filename}  帧 {first_frame['frame_index']}",
        f"{second_job.filename}  帧 {second_frame['frame_index']}",
    ]
    frames = [first_frame, second_frame]

    draw.text((60, 34), "华羽羽毛球击球动作对比", fill="#1f2933", font=title_font)
    for rect, title, frame in zip(panels, titles, frames, strict=True):
        draw.rounded_rectangle(rect, radius=8, fill=panel_fill, outline="#d7cdbb", width=2)
        draw.text((rect[0] + 22, rect[1] + 20), title[:78], fill="#1f2933", font=font)
        render_pose_into_panel(draw, rect, frame, bone_color, joint_color, accent)

    output_path = settings.comparison_dir / f"{comparison_id}.png"
    image.save(output_path)
    register_comparison(comparison_id, output_path)
    return output_path


def render_pose_into_panel(
    draw: Any,
    rect: tuple[int, int, int, int],
    frame: dict[str, Any],
    bone_color: str,
    joint_color: str,
    accent: str,
) -> None:
    players = frame.get("players") or []
    if not players:
        draw.text((rect[0] + 22, rect[1] + 60), "该帧未检测到人体", fill="#8a6d3b")
        return
    skeleton = players[0]  # compare the primary (left-most) player
    kp = {item["id"]: item for item in skeleton["keypoints"]}
    render_ids = [index for index in POSE_RENDER_IDS if index in kp]
    xs = [kp[index]["x"] for index in render_ids]
    ys = [kp[index]["y"] for index in render_ids]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    source_w = max(0.001, max_x - min_x)
    source_h = max(0.001, max_y - min_y)
    panel_w = rect[2] - rect[0]
    panel_h = rect[3] - rect[1]
    scale = min(panel_w * 0.68 / source_w, panel_h * 0.68 / source_h)
    center_x = rect[0] + panel_w * 0.5
    center_y = rect[1] + panel_h * 0.54
    pose_center_x = (min_x + max_x) / 2
    pose_center_y = (min_y + max_y) / 2

    def xy(index: int) -> tuple[float, float]:
        landmark = kp[index]
        return (
            center_x + (landmark["x"] - pose_center_x) * scale,
            center_y + (landmark["y"] - pose_center_y) * scale,
        )

    for start, end in MEDIAPIPE_BONES:
        if start in kp and end in kp:
            draw.line((*xy(start), *xy(end)), fill=bone_color, width=8)

    for index in render_ids:
        x, y = xy(index)
        radius = 8 if index in {14, 16, 26, 28} else 6
        fill = accent if index in {14, 16} else joint_color
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=fill)

    angles = skeleton["angles"]
    metrics = [
        f"右肘角度 {angles['right_elbow']:.1f}度",
        f"右膝角度 {angles['right_knee']:.1f}度",
        f"躯干旋转 {angles['trunk_rotation']:.1f}度",
    ]
    for index, metric in enumerate(metrics):
        draw.text((rect[0] + 22, rect[3] - 92 + index * 24), metric, fill="#25313b")
