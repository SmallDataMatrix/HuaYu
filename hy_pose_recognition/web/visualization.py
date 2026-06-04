from __future__ import annotations

from typing import Any

import matplotlib.pyplot as plt
import pandas as pd
from PIL import Image, ImageDraw, ImageFont

from hy_pose_recognition.models import AnalysisJob
from hy_pose_recognition.services.landmarks import MEDIAPIPE_BONES, POSE_RENDER_IDS
from hy_pose_recognition.web.fonts import load_chinese_font


ZONE_LABELS = {
    "front_left": "前场左区",
    "front_right": "前场右区",
    "mid_left": "中场左区",
    "mid_right": "中场右区",
    "rear_left": "后场左区",
    "rear_right": "后场右区",
}


def angle_dataframe(job: AnalysisJob) -> pd.DataFrame:
    rows = []
    for frame in job.frames:
        angles = frame["skeleton"]["angles"]
        rows.append(
            {
                "time_sec": frame["timestamp_ms"] / 1000,
                "right_elbow": angles["right_elbow"],
                "right_knee": angles["right_knee"],
                "trunk_rotation": angles["trunk_rotation"],
                "right_shoulder": angles["right_shoulder"],
            }
        )
    return pd.DataFrame(rows)


def landing_dataframe(job: AnalysisJob) -> pd.DataFrame:
    rows = []
    for landing in job.landings:
        rows.append(
            {
                "time_sec": landing["timestamp_ms"] / 1000,
                "x": landing["court_coord"]["x"],
                "y": landing["court_coord"]["y"],
                "zone": ZONE_LABELS.get(landing["zone"], landing["zone"]),
                "in_bounds": "是" if landing["in_bounds"] else "否",
            }
        )
    return pd.DataFrame(rows)


def current_frame(job: AnalysisJob, ratio: float) -> dict[str, Any]:
    if not job.frames:
        raise ValueError("任务没有可用帧数据")
    frame_index = round(max(0.0, min(1.0, ratio)) * (len(job.frames) - 1))
    return job.frames[frame_index]


def render_keyframe(job: AnalysisJob, frame_index: int, size: tuple[int, int] = (960, 540)) -> Image.Image:
    frame_index = max(0, min(frame_index, len(job.frames) - 1))
    frame = job.frames[frame_index]
    image = Image.new("RGB", size, "#151a1f")
    draw = ImageDraw.Draw(image)
    draw_video_grid(draw, size)
    draw_shuttle_trace(draw, job, frame_index, size)
    draw_pose(draw, frame, size)

    font = load_chinese_font(18)
    timestamp = frame["timestamp_ms"] / 1000
    draw.rounded_rectangle((18, 16, 330, 54), radius=8, fill="#fffaf1")
    draw.text((30, 27), f"{job.filename[:18]}  时间 {timestamp:.2f}秒", fill="#1f2933", font=font)
    return image


def draw_video_grid(draw: ImageDraw.ImageDraw, size: tuple[int, int]) -> None:
    width, height = size
    draw.rectangle((0, height * 0.72, width, height), fill="#1c2d2f")
    for index in range(1, 4):
        x = width * index / 4
        draw.line((x, height * 0.72, x, height), fill="#2c4847", width=2)
    draw.line((0, height * 0.86, width, height * 0.86), fill="#2c4847", width=2)


def draw_pose(draw: ImageDraw.ImageDraw, frame: dict[str, Any], size: tuple[int, int]) -> None:
    width, height = size
    kp = {item["id"]: item for item in frame["skeleton"]["keypoints"]}
    for start, end in MEDIAPIPE_BONES:
        draw.line(
            (
                kp[start]["x"] * width,
                kp[start]["y"] * height,
                kp[end]["x"] * width,
                kp[end]["y"] * height,
            ),
            fill="#22d3c5",
            width=7,
        )
    for index in POSE_RENDER_IDS:
        item = kp[index]
        radius = 8 if index in {14, 16} else 6
        fill = "#ff6a3d" if index in {14, 16} else "#f9fafb"
        x = item["x"] * width
        y = item["y"] * height
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=fill)


def draw_shuttle_trace(draw: ImageDraw.ImageDraw, job: AnalysisJob, frame_index: int, size: tuple[int, int]) -> None:
    width, height = size
    points = []
    for frame in job.frames[max(0, frame_index - 10) : frame_index + 1]:
        shuttle = frame["shuttle"]
        if shuttle["detected"] and shuttle["center"]:
            points.append((shuttle["center"][0] * width, shuttle["center"][1] * height))
    if len(points) < 2:
        return
    for index, point in enumerate(points[1:], start=1):
        previous = points[index - 1]
        draw.line((*previous, *point), fill="#f5b82e", width=4)
        radius = 5 + index // 4
        draw.ellipse((point[0] - radius, point[1] - radius, point[0] + radius, point[1] + radius), fill="#e24d2e")


def court_figure(job: AnalysisJob):
    fig, ax = plt.subplots(figsize=(4.6, 5.8))
    fig.patch.set_facecolor("#fbfaf6")
    ax.set_facecolor("#d6efe6")
    ax.set_xlim(0, 1)
    ax.set_ylim(1, 0)
    ax.axis("off")

    line_color = "#217a65"
    ax.plot([0.08, 0.92, 0.92, 0.08, 0.08], [0.04, 0.04, 0.96, 0.96, 0.04], color=line_color, linewidth=2.5)
    ax.plot([0.5, 0.5], [0.04, 0.96], color=line_color, linewidth=2)
    ax.plot([0.08, 0.92], [0.37, 0.37], color=line_color, linewidth=2)
    ax.plot([0.08, 0.92], [0.67, 0.67], color=line_color, linewidth=2)

    for landing in job.landings:
        x = landing["court_coord"]["x"]
        y = landing["court_coord"]["y"]
        color = "#e24d2e" if landing["in_bounds"] else "#4b5563"
        ax.scatter([x], [y], s=90, color=color, edgecolor="#ffffff", linewidth=1.5, zorder=3)
    return fig


def comparison_bytes(path) -> bytes:
    return path.read_bytes()
