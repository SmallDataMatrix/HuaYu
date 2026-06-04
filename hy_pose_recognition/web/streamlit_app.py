from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import streamlit as st
import streamlit.components.v1 as components

from hy_pose_recognition.core import settings
from hy_pose_recognition.models import AnalysisJob
from hy_pose_recognition.services.comparison import frame_for, render_skeleton_png
from hy_pose_recognition.web.labels import ANGLE_LABELS, LANDING_LABELS, STROKE_TABLE_LABELS
from hy_pose_recognition.web.motion_player import build_motion_player_html
from hy_pose_recognition.web.visualization import (
    angle_dataframe,
    comparison_bytes,
    court_figure,
    landing_dataframe,
)
from hy_pose_recognition.web.workflow import create_job_from_upload


def main() -> None:
    st.set_page_config(page_title=settings.app_title, page_icon="HY", layout="wide", initial_sidebar_state="expanded")
    inject_style()
    initialize_state()

    render_header()
    render_upload_panel()

    jobs: list[AnalysisJob] = st.session_state.jobs
    if not jobs:
        render_empty_workspace()
    else:
        render_workspace(jobs)

    render_disclaimer_banner()


def initialize_state() -> None:
    if "pose_page_ready" not in st.session_state:
        import shutil
        for d in (settings.upload_dir, settings.processed_dir, settings.comparison_dir):
            shutil.rmtree(d, ignore_errors=True)
            d.mkdir(parents=True, exist_ok=True)
        st.session_state.jobs = []
        st.session_state.comparison_path = None
        st.session_state.pose_page_ready = True
    st.session_state.setdefault("jobs", [])
    st.session_state.setdefault("comparison_path", None)
    st.session_state.setdefault("custom_primary", False)
    st.session_state.setdefault("custom_comparison", False)


def render_disclaimer_banner() -> None:
    st.markdown(
        '<div style="background:#fffbeb;border:1px solid #f59e0b;border-radius:8px;'
        'padding:8px 14px;margin-top:40px;font-size:12px;color:#92400e">'
        '⚠️ <b>仅供演示</b>：本工具为求职作品集演示项目，不以任何商业目的设计或运营，'
        '使用者须自行遵守相关法律法规。'
        '</div>',
        unsafe_allow_html=True,
    )


def render_header() -> None:
    st.markdown(
        """
        <section class="hy-header">
            <div class="hy-mark">HY</div>
            <div>
                <h1>华羽AI羽毛球训练分析</h1>
                <p>羽毛球训练动作复盘演示工作台</p>
            </div>
        </section>
        """,
        unsafe_allow_html=True,
    )


_SAMPLE_PRIMARY = settings.project_root / "data" / "sample_video" / "Kexin.mp4"
_SAMPLE_COMPARISON = settings.project_root / "data" / "sample_video" / "coach.mp4"


def _resolve_video(upload, sample_path: "Path") -> tuple[str, bytes] | None:
    """Return (filename, bytes) from upload widget or sample file; None if neither exists."""
    if upload is not None:
        return upload.name, upload.getvalue()
    if sample_path.exists():
        return sample_path.name, sample_path.read_bytes()
    return None


def _video_slot(label: str, sample_path: Path, state_key: str, uploader_key: str):
    """Render one video slot: sample card by default, file-uploader when user requests custom."""
    st.markdown(f"**{label}**")
    if not st.session_state[state_key]:
        # ── sample is active ──────────────────────────────────────────
        st.markdown(
            f'<div style="border:1px solid #d1d5db;border-radius:8px;'
            f'padding:10px 14px;background:#f9fafb;font-size:13px;color:#374151;'
            f'display:flex;align-items:center;gap:8px;margin-bottom:6px">'
            f'📹 <span>{sample_path.name}</span>'
            f'<span style="background:#e0f2fe;color:#0369a1;font-size:11px;'
            f'padding:1px 7px;border-radius:10px;margin-left:4px">内置样本</span>'
            f'</div>',
            unsafe_allow_html=True,
        )
        if st.button("更换视频", key=f"swap_{state_key}", use_container_width=True):
            st.session_state[state_key] = True
            st.rerun()
        return None  # will use sample
    else:
        # ── uploader is active ────────────────────────────────────────
        uploaded = st.file_uploader(label, type=["mp4", "mov", "avi"], key=uploader_key,
                                    label_visibility="collapsed")
        if st.button("↩ 恢复内置样本", key=f"restore_{state_key}", use_container_width=True):
            st.session_state[state_key] = False
            st.rerun()
        return uploaded


@st.dialog("正在分析", width="small")
def _analysis_dialog(primary, comparison) -> None:
    resolved = [
        _resolve_video(primary, _SAMPLE_PRIMARY),
        _resolve_video(comparison, _SAMPLE_COMPARISON),
    ]
    resolved = [v for v in resolved if v is not None]
    if not resolved:
        st.warning("请至少选择一个视频。")
        if st.button("关闭"):
            st.rerun()
        return

    st.info(
        "⏳ 本演示使用免费算力，分析可能需要 **3–5 分钟**，"
        "请耐心等待，期间请勿关闭或刷新页面。"
    )

    st.session_state.comparison_path = None
    st.session_state.jobs = []
    progress = st.progress(0, text="正在准备分析…")
    jobs = []
    for index, (name, data) in enumerate(resolved, start=1):
        progress.progress((index - 1) / len(resolved), text=f"正在分析：{name}")
        try:
            jobs.append(create_job_from_upload(name, data))
        except ValueError as exc:
            progress.progress(1.0, text="分析失败")
            st.error(f"{name} 分析失败：{exc}")
            return
    progress.progress(1.0, text="✓ 分析完成")
    st.session_state.jobs = jobs
    st.rerun()


def render_upload_panel() -> None:
    with st.container(border=True):
        first, second, action = st.columns([1, 1, 0.28], vertical_alignment="bottom")
        with first:
            primary = _video_slot("训练视频", _SAMPLE_PRIMARY, "custom_primary", "primary_video")
        with second:
            comparison = _video_slot("对比视频", _SAMPLE_COMPARISON, "custom_comparison", "comparison_video")
        with action:
            submitted = st.button("开始分析", type="primary", use_container_width=True)
        st.caption(f"默认加载内置样本视频，点击「更换视频」可上传自定义视频 · 时长请控制在 {settings.max_upload_seconds} 秒以内。")

        if submitted:
            _analysis_dialog(primary, comparison)


def render_empty_workspace() -> None:
    left, right = st.columns([2, 1])
    with left:
        st.container(border=True).markdown(
            '<div class="empty-panel">直接点击「开始分析」即可使用内置样本视频，或上传自己的训练视频。</div>',
            unsafe_allow_html=True,
        )
    with right:
        st.container(border=True).markdown(
            '<div class="empty-panel compact">姿态骨架、球路轨迹、落点统计和对比图片会显示在这里。</div>',
            unsafe_allow_html=True,
        )


def render_workspace(jobs: list[AnalysisJob]) -> None:
    primary = jobs[0]
    comparison = jobs[1] if len(jobs) > 1 else None

    video_columns = st.columns(2 if comparison else 1)
    render_motion_panel(video_columns[0], primary, "训练视频")
    if comparison:
        render_motion_panel(video_columns[1], comparison, "对比视频")

    st.divider()
    strokes_tab, court_tab, angles_tab, compare_tab = st.tabs(["击球数据", "落点统计", "角度变化", "对比图片"])
    with strokes_tab:
        render_stroke_table(primary)
    with court_tab:
        render_landing_panel(primary)
    with angles_tab:
        render_angle_panel(primary)
    with compare_tab:
        render_comparison_panel(primary, comparison)


def render_motion_panel(column, job: AnalysisJob, title: str) -> None:
    with column:
        components.html(build_motion_player_html(job, title), height=900, scrolling=False)


def render_stroke_table(job: AnalysisJob) -> None:
    rows = []
    for index, stroke in enumerate(job.strokes, start=1):
        rows.append(
            {
                "stroke": index,
                "contact_sec": stroke["timestamp_ms"] / 1000,
                "prep": stroke["keyframes"]["preparation"],
                "contact": stroke["keyframes"]["contact"],
                "follow": stroke["keyframes"]["follow_through"],
            }
        )
    st.dataframe(
        rows,
        column_config=STROKE_TABLE_LABELS,
        use_container_width=True,
        hide_index=True,
    )


def render_landing_panel(job: AnalysisJob) -> None:
    st.subheader("落点统计")
    st.pyplot(court_figure(job), use_container_width=True)
    landings = landing_dataframe(job)
    if not landings.empty:
        st.dataframe(
            landings,
            column_config=LANDING_LABELS,
            use_container_width=True,
            hide_index=True,
        )


def render_angle_panel(job: AnalysisJob) -> None:
    st.subheader("角度变化")

    # Collect all player ids that appear across frames
    player_ids = sorted({
        p["player_id"]
        for frame in job.frames
        for p in frame.get("players", [])
    })

    if not player_ids:
        st.info("暂无角度数据。")
        return

    if len(player_ids) > 1:
        selected = int(st.selectbox(
            "选择运动员",
            player_ids,
            format_func=lambda pid: f"运动员 {pid + 1}",
            key="angle_player_select",
        ) or player_ids[0])
    else:
        selected = player_ids[0]

    angles = angle_dataframe(job, player_id=selected)
    if angles.empty:
        st.info("该运动员暂无角度数据。")
        return
    display_angles = angles.rename(columns=ANGLE_LABELS)
    st.line_chart(
        display_angles.set_index("时间(秒)")[["右肘角度", "右膝角度", "躯干旋转", "右肩角度"]],
        use_container_width=True,
    )


def render_comparison_panel(primary: AnalysisJob, comparison: AnalysisJob | None) -> None:
    with st.container(border=True):
        st.subheader("对比图片")
        first_options = frame_options(primary)
        second_job = comparison or primary
        second_options = frame_options(second_job)
        left, right, action = st.columns([1, 1, 0.35], vertical_alignment="bottom")
        with left:
            first_label = st.selectbox("第一个时刻", list(first_options), key="first_frame")
        with right:
            second_label = st.selectbox("第二个时刻", list(second_options), index=len(second_options) - 1, key="second_frame")
        with action:
            generate = st.button("生成", type="primary", use_container_width=True)

        if generate:
            first_frame = frame_for(primary, first_options[first_label], "first")
            second_frame = frame_for(second_job, second_options[second_label], "last")
            comparison_id = str(uuid4())
            path = render_skeleton_png(comparison_id, primary, first_frame, second_job, second_frame)
            st.session_state.comparison_path = path

        if st.session_state.comparison_path:
            path = st.session_state.comparison_path
            st.image(str(path), use_container_width=True)
            st.download_button(
                "下载PNG",
                data=comparison_bytes(path),
                file_name=path.name,
                mime="image/png",
                use_container_width=True,
            )


def frame_options(job: AnalysisJob) -> dict[str, int]:
    options: dict[str, int] = {}
    for index, stroke in enumerate(job.strokes, start=1):
        options[f"第{index}次击球：准备"] = stroke["keyframes"]["preparation"]
        options[f"第{index}次击球：触球"] = stroke["keyframes"]["contact"]
        options[f"第{index}次击球：随挥"] = stroke["keyframes"]["follow_through"]
    if not options and job.frames:
        options["第一帧"] = 0
        options["最后一帧"] = len(job.frames) - 1
    return options


def inject_style() -> None:
    st.markdown(
        """
        <style>
          .stApp {
            background: #fbfaf6;
            color: #1f2933;
          }
          .hy-header {
            display: flex;
            gap: 14px;
            align-items: center;
            padding: 10px 0 18px;
          }
.hy-mark {
            width: 46px;
            height: 46px;
            display: grid;
            place-items: center;
            border-radius: 8px;
            background: #1f2933;
            color: white;
            font-weight: 800;
          }
          .hy-header h1 {
            margin: 0;
            font-size: 26px;
            line-height: 1.1;
            letter-spacing: 0;
          }
          .hy-header p {
            margin: 4px 0 0;
            color: #66727f;
          }
          .empty-panel {
            min-height: 360px;
            display: grid;
            place-items: center;
            color: #66727f;
            font-size: 18px;
            text-align: center;
          }
          .empty-panel.compact {
            min-height: 180px;
            font-size: 15px;
          }
          div[data-testid="stMetricValue"] {
            color: #0b6f87;
          }
          .stButton > button {
            border-radius: 8px;
          }
        </style>
        """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
