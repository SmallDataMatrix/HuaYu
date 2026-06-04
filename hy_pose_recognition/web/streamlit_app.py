from __future__ import annotations

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
    st.set_page_config(page_title=settings.app_title, page_icon="HY", layout="wide")
    inject_style()
    initialize_state()

    render_disclaimer_banner()
    render_header()

    render_upload_panel()

    jobs: list[AnalysisJob] = st.session_state.jobs
    if not jobs:
        render_empty_workspace()
        return

    render_workspace(jobs)


def initialize_state() -> None:
    st.session_state.setdefault("jobs", [])
    st.session_state.setdefault("comparison_path", None)


def render_disclaimer_banner() -> None:
    st.markdown(
        """
        <section class="demo-disclaimer">
          <strong>演示声明：</strong>
          本最小可行版本工具仅作为求职作品演示使用，不面向任何商业或经营用途；
          因不当使用产生的任何法律后果，作者不承担责任。
        </section>
        """,
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


def render_upload_panel() -> None:
    with st.container(border=True):
        first, second, action = st.columns([1, 1, 0.28], vertical_alignment="bottom")
        with first:
            primary = st.file_uploader("训练视频", type=["mp4", "mov", "avi"], key="primary_video")
        with second:
            comparison = st.file_uploader("对比视频", type=["mp4", "mov", "avi"], key="comparison_video")
        with action:
            submitted = st.button("开始分析", type="primary", use_container_width=True)
        st.caption(f"受当前计算能力限制，上传视频时长请控制在 {settings.max_upload_seconds} 秒以内。")

        if submitted:
            uploads = [file for file in (primary, comparison) if file is not None]
            if not uploads:
                st.warning("请至少选择一个视频。")
                return

            st.session_state.comparison_path = None
            st.session_state.jobs = []
            progress = st.progress(0, text="正在准备分析")
            jobs = []
            for index, upload in enumerate(uploads, start=1):
                progress.progress((index - 1) / len(uploads), text=f"正在分析：{upload.name}")
                try:
                    jobs.append(create_job_from_upload(upload.name, upload.getvalue()))
                except ValueError as exc:
                    progress.progress(1.0, text="分析失败")
                    st.error(f"{upload.name} 上传失败：{exc}")
                    return
            progress.progress(1.0, text="分析完成")
            st.session_state.jobs = jobs
            st.rerun()


def render_empty_workspace() -> None:
    left, right = st.columns([2, 1])
    with left:
        st.container(border=True).markdown(
            '<div class="empty-panel">上传训练视频后即可打开分析工作台。</div>',
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
    angles = angle_dataframe(job)
    if angles.empty:
        st.info("暂无角度数据。")
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
          .demo-disclaimer {
            border: 1px solid #f0c36a;
            border-left: 6px solid #e24d2e;
            background: #fff6dd;
            color: #40331d;
            border-radius: 8px;
            padding: 12px 14px;
            margin: 0 0 12px;
            font-size: 14px;
            line-height: 1.45;
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
