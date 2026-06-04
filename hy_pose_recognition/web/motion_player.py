from __future__ import annotations

import base64
import html
import json
from pathlib import Path
from typing import Any

from hy_pose_recognition.models import AnalysisJob
from hy_pose_recognition.services.landmarks import MEDIAPIPE_BONES, POSE_RENDER_IDS


VIDEO_MIME_TYPES = {
    ".avi": "video/x-msvideo",
    ".mov": "video/quicktime",
    ".mp4": "video/mp4",
}


def build_motion_player_html(job: AnalysisJob, title: str) -> str:
    """Build a self-contained video player with real-time pose overlay."""
    frames = [_frame_payload(frame) for frame in job.frames]
    video_path = job.annotated_video_path or job.video_path
    video_source = _video_data_uri(video_path)
    has_annotated_video = job.annotated_video_path is not None
    payload = {
        "title": title,
        "filename": job.filename,
        "durationSec": job.duration_sec,
        "frameCount": job.frame_count,
        "strokes": job.strokes,
        "landings": job.landings,
        "frames": frames,
        "bones": MEDIAPIPE_BONES,
        "poseIds": sorted(POSE_RENDER_IDS),
        "drawOverlay": not has_annotated_video,
    }

    payload_json = _json_for_script(payload)

    return f"""
    <div class="motion-player" data-player>
      <div class="player-header">
        <div>
          <h3>{html.escape(title)}</h3>
          <p>{html.escape(job.filename)}</p>
        </div>
        <div class="status-pill">{"骨架已写入视频" if has_annotated_video else "实时骨架叠加"}</div>
      </div>
      <div class="stage">
        <video data-video preload="metadata" playsinline>
          <source src="{video_source}" type="{_video_mime_type(video_path)}">
        </video>
        <canvas data-canvas></canvas>
      </div>
      <div class="controls">
        <button type="button" data-toggle>播放</button>
        <input data-seek type="range" min="0" max="1000" value="0" step="1" aria-label="视频进度">
        <span data-time>0.00 / {job.duration_sec:.2f}s</span>
      </div>
      <div class="phase" data-phase>等待播放</div>
      <div class="metric-grid">
        <div><span>当前帧</span><strong data-frame>0</strong></div>
        <div><span>击球次数</span><strong>{len(job.strokes)}</strong></div>
        <div><span>落点数量</span><strong>{len(job.landings)}</strong></div>
        <div><span>右肘角度</span><strong data-elbow>--</strong></div>
        <div><span>右膝角度</span><strong data-knee>--</strong></div>
        <div><span>躯干旋转</span><strong data-trunk>--</strong></div>
        <div><span>右肩角度</span><strong data-shoulder>--</strong></div>
        <div><span>羽球检测</span><strong data-shuttle>--</strong></div>
      </div>
    </div>
    <script type="application/json" data-payload>{payload_json}</script>
    <script>
      (() => {{
        const root = document.currentScript.previousElementSibling.previousElementSibling;
        const payload = JSON.parse(root.nextElementSibling.textContent);
        const video = root.querySelector("[data-video]");
        const canvas = root.querySelector("[data-canvas]");
        const ctx = canvas.getContext("2d");
        const toggle = root.querySelector("[data-toggle]");
        const seek = root.querySelector("[data-seek]");
        const timeLabel = root.querySelector("[data-time]");
        const phaseLabel = root.querySelector("[data-phase]");
        const frameLabel = root.querySelector("[data-frame]");
        const elbowLabel = root.querySelector("[data-elbow]");
        const kneeLabel = root.querySelector("[data-knee]");
        const trunkLabel = root.querySelector("[data-trunk]");
        const shoulderLabel = root.querySelector("[data-shoulder]");
        const shuttleLabel = root.querySelector("[data-shuttle]");
        const frames = payload.frames || [];
        const durationMs = Math.max(1, payload.durationSec * 1000);
        let seeking = false;

        function resizeCanvas() {{
          const rect = video.getBoundingClientRect();
          const scale = window.devicePixelRatio || 1;
          canvas.width = Math.max(1, Math.round(rect.width * scale));
          canvas.height = Math.max(1, Math.round(rect.height * scale));
          canvas.style.width = `${{rect.width}}px`;
          canvas.style.height = `${{rect.height}}px`;
          ctx.setTransform(scale, 0, 0, scale, 0, 0);
        }}

        function frameForTime(currentTime) {{
          if (!frames.length) return null;
          const index = Math.round((currentTime * 1000 / durationMs) * (frames.length - 1));
          return frames[Math.max(0, Math.min(frames.length - 1, index))];
        }}

        function drawPose(frame, width, height) {{
          const keypoints = new Map(frame.keypoints.map((item) => [item.id, item]));
          ctx.lineCap = "round";
          ctx.lineJoin = "round";
          ctx.strokeStyle = "rgba(20, 184, 166, 0.95)";
          ctx.lineWidth = 5;
          for (const [start, end] of payload.bones) {{
            const a = keypoints.get(start);
            const b = keypoints.get(end);
            if (!a || !b) continue;
            ctx.beginPath();
            ctx.moveTo(a.x * width, a.y * height);
            ctx.lineTo(b.x * width, b.y * height);
            ctx.stroke();
          }}
          for (const id of payload.poseIds) {{
            const point = keypoints.get(id);
            if (!point) continue;
            const active = id === 14 || id === 16;
            ctx.beginPath();
            ctx.fillStyle = active ? "#f97316" : "#f8fafc";
            ctx.arc(point.x * width, point.y * height, active ? 6 : 5, 0, Math.PI * 2);
            ctx.fill();
            ctx.lineWidth = 2;
            ctx.strokeStyle = "rgba(15, 23, 42, 0.65)";
            ctx.stroke();
          }}
        }}

        function drawShuttle(frame, width, height) {{
          const index = frame.frameIndex;
          const trace = frames.slice(Math.max(0, index - 10), index + 1)
            .map((item) => item.shuttle && item.shuttle.center)
            .filter(Boolean);
          if (!trace.length) return;
          ctx.strokeStyle = "#fbbf24";
          ctx.fillStyle = "#ef4444";
          ctx.lineWidth = 3;
          ctx.beginPath();
          trace.forEach((point, idx) => {{
            const x = point[0] * width;
            const y = point[1] * height;
            if (idx === 0) ctx.moveTo(x, y);
            else ctx.lineTo(x, y);
          }});
          ctx.stroke();
          const last = trace[trace.length - 1];
          ctx.beginPath();
          ctx.arc(last[0] * width, last[1] * height, 5, 0, Math.PI * 2);
          ctx.fill();
        }}

        function phaseForFrame(frameIndex) {{
          for (let i = 0; i < payload.strokes.length; i += 1) {{
            const stroke = payload.strokes[i];
            const keys = stroke.keyframes || {{}};
            if (frameIndex >= keys.preparation && frameIndex < keys.contact) {{
              return `第${{i + 1}}次击球：准备阶段`;
            }}
            if (frameIndex === keys.contact) {{
              return `第${{i + 1}}次击球：触球瞬间`;
            }}
            if (frameIndex > keys.contact && frameIndex <= keys.follow_through) {{
              return `第${{i + 1}}次击球：随挥阶段`;
            }}
          }}
          return video.paused ? "已暂停，可拖动进度条查看动作" : "播放中，等待下一次击球";
        }}

        function updateMetrics(frame) {{
          const angles = frame.angles || {{}};
          frameLabel.textContent = frame.frameIndex;
          elbowLabel.textContent = `${{Math.round(angles.right_elbow || 0)}}度`;
          kneeLabel.textContent = `${{Math.round(angles.right_knee || 0)}}度`;
          trunkLabel.textContent = `${{Math.round(angles.trunk_rotation || 0)}}度`;
          shoulderLabel.textContent = `${{Math.round(angles.right_shoulder || 0)}}度`;
          shuttleLabel.textContent = frame.shuttle && frame.shuttle.detected ? "已检测" : "未检测";
          phaseLabel.textContent = phaseForFrame(frame.frameIndex);
        }}

        function draw() {{
          resizeCanvas();
          const width = video.clientWidth;
          const height = video.clientHeight;
          ctx.clearRect(0, 0, width, height);
          const frame = frameForTime(video.currentTime);
          if (frame) {{
            if (payload.drawOverlay) {{
              drawShuttle(frame, width, height);
              drawPose(frame, width, height);
            }}
            updateMetrics(frame);
          }}
          if (!seeking) {{
            const duration = video.duration || payload.durationSec || 1;
            seek.value = Math.round((video.currentTime / duration) * 1000);
          }}
          const total = video.duration || payload.durationSec || 0;
          timeLabel.textContent = `${{video.currentTime.toFixed(2)}} / ${{total.toFixed(2)}}s`;
          toggle.textContent = video.paused ? "播放" : "暂停";
          window.requestAnimationFrame(draw);
        }}

        toggle.addEventListener("click", () => {{
          if (video.paused) video.play();
          else video.pause();
        }});
        seek.addEventListener("input", () => {{
          seeking = true;
          const duration = video.duration || payload.durationSec || 0;
          video.currentTime = Number(seek.value) / 1000 * duration;
          seeking = false;
        }});
        video.addEventListener("click", () => {{
          if (video.paused) video.play();
          else video.pause();
        }});
        video.addEventListener("loadedmetadata", resizeCanvas);
        window.addEventListener("resize", resizeCanvas);
        window.requestAnimationFrame(draw);
      }})();
    </script>
    <style>
      .motion-player {{
        background: #ffffff;
        border: 1px solid #d8e0e6;
        border-radius: 8px;
        color: #1f2933;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        padding: 14px;
      }}
      .player-header {{
        align-items: center;
        display: flex;
        justify-content: space-between;
        gap: 12px;
        margin-bottom: 10px;
      }}
      .player-header h3 {{
        font-size: 18px;
        line-height: 1.2;
        margin: 0;
      }}
      .player-header p {{
        color: #66727f;
        font-size: 13px;
        margin: 3px 0 0;
        overflow-wrap: anywhere;
      }}
      .status-pill {{
        background: #e8f7f4;
        border: 1px solid #b8e2da;
        border-radius: 999px;
        color: #0f766e;
        flex: 0 0 auto;
        font-size: 12px;
        padding: 5px 9px;
      }}
      .stage {{
        background: #111827;
        border-radius: 8px;
        overflow: hidden;
        position: relative;
        width: 100%;
      }}
      video {{
        display: block;
        width: 100%;
      }}
      canvas {{
        inset: 0;
        pointer-events: none;
        position: absolute;
      }}
      .controls {{
        align-items: center;
        display: grid;
        grid-template-columns: 76px 1fr 112px;
        gap: 10px;
        margin-top: 10px;
      }}
      button {{
        background: #0b6f87;
        border: 0;
        border-radius: 8px;
        color: #ffffff;
        cursor: pointer;
        font-size: 14px;
        height: 36px;
      }}
      input[type="range"] {{
        accent-color: #0b6f87;
        width: 100%;
      }}
      .controls span,
      .phase {{
        color: #526170;
        font-size: 13px;
      }}
      .phase {{
        background: #f5f7f8;
        border-radius: 8px;
        margin-top: 10px;
        padding: 9px 10px;
      }}
      .metric-grid {{
        display: grid;
        gap: 8px;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        margin-top: 10px;
      }}
      .metric-grid div {{
        background: #fbfaf6;
        border: 1px solid #e6e0d2;
        border-radius: 8px;
        min-width: 0;
        padding: 9px 10px;
      }}
      .metric-grid span {{
        color: #66727f;
        display: block;
        font-size: 12px;
        margin-bottom: 4px;
      }}
      .metric-grid strong {{
        color: #1f2933;
        display: block;
        font-size: 18px;
        line-height: 1.2;
      }}
      @media (max-width: 720px) {{
        .controls {{
          grid-template-columns: 72px 1fr;
        }}
        .controls span {{
          grid-column: 1 / -1;
        }}
        .metric-grid {{
          grid-template-columns: repeat(2, minmax(0, 1fr));
        }}
      }}
    </style>
    """


def _frame_payload(frame: dict[str, Any]) -> dict[str, Any]:
    return {
        "frameIndex": frame["frame_index"],
        "timestampMs": frame["timestamp_ms"],
        "keypoints": frame["skeleton"]["keypoints"],
        "angles": frame["skeleton"]["angles"],
        "shuttle": frame["shuttle"],
    }


def _video_data_uri(video_path: Path) -> str:
    encoded = base64.b64encode(video_path.read_bytes()).decode("ascii")
    return f"data:{_video_mime_type(video_path)};base64,{encoded}"


def _video_mime_type(video_path: Path) -> str:
    return VIDEO_MIME_TYPES.get(video_path.suffix.lower(), "video/mp4")


def _json_for_script(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
