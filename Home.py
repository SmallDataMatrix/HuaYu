import streamlit as st

st.set_page_config(page_title="华羽 · SmallDataMatrix", page_icon="🏸", layout="wide")

st.markdown(
    """
    <style>
      .profile-header { display:flex; gap:24px; align-items:center; padding:20px 0 10px; }
      .avatar {
        width:80px; height:80px; border-radius:50%;
        background:#1f2933; color:white; display:grid;
        place-items:center; font-size:28px; font-weight:800; flex-shrink:0;
      }
      .tag {
        display:inline-block; background:#f0f4f8; color:#3d5a80;
        border-radius:12px; padding:3px 10px; font-size:13px; margin:3px 4px 3px 0;
      }
      .section-title { font-size:18px; font-weight:700; margin:28px 0 10px; border-bottom:2px solid #e8e8e8; padding-bottom:6px; }
      .tool-card {
        border:1px solid #e0e0e0; border-radius:12px; padding:20px 22px;
        background:#fafafa; transition:box-shadow .2s;
      }
      .tool-card:hover { box-shadow:0 4px 16px rgba(0,0,0,.08); }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── Profile header ────────────────────────────────────────────────────────────
st.markdown(
    """
    <div class="profile-header">
      <div class="avatar">HY</div>
      <div>
        <h1 style="margin:0;font-size:30px">Hua Yu &nbsp;<span style="font-size:16px;color:#66727f;font-weight:400">/ SmallDataMatrix</span></h1>
        <p style="margin:4px 0 8px;color:#66727f;font-size:15px">Data Scientist · ML Engineer · Sports Analytics</p>
        <span class="tag">Python</span>
        <span class="tag">Machine Learning</span>
        <span class="tag">Computer Vision</span>
        <span class="tag">NLP / LLM</span>
        <span class="tag">Streamlit</span>
        <span class="tag">Data Visualization</span>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── About ─────────────────────────────────────────────────────────────────────
st.markdown('<div class="section-title">About</div>', unsafe_allow_html=True)
st.markdown(
    """
Data scientist with a strong focus on practical, reliable implementation. I enjoy turning raw, messy data into
actionable insights — whether that's analyzing athletes' movement patterns with computer vision or mining
real user opinions from social media at scale.

My work spans the full stack: data collection and cleaning, model development, and interactive web tools
that make complex analyses accessible.
"""
)

# ── Skills ────────────────────────────────────────────────────────────────────
st.markdown('<div class="section-title">Skills</div>', unsafe_allow_html=True)
col1, col2, col3 = st.columns(3)
with col1:
    st.markdown("**Data & ML**")
    st.markdown("- Pandas · NumPy · Scikit-learn\n- PyTorch · JAX\n- MediaPipe · OpenCV\n- SQL · DuckDB")
with col2:
    st.markdown("**LLM & NLP**")
    st.markdown("- Prompt engineering\n- OpenAI / DeepSeek API\n- Opinion mining (VOC)\n- RAG pipelines")
with col3:
    st.markdown("**Engineering**")
    st.markdown("- Streamlit · FastAPI\n- Docker · GitHub Actions\n- Python packaging\n- REST API design")

# ── Projects ──────────────────────────────────────────────────────────────────
st.markdown('<div class="section-title">Projects</div>', unsafe_allow_html=True)

c1, c2 = st.columns(2, gap="large")

with c1:
    st.markdown(
        """
        <div class="tool-card">
          <div style="font-size:22px;margin-bottom:6px">🎯 华羽AI羽毛球训练分析</div>
          <div style="color:#66727f;font-size:13px;margin-bottom:12px">Computer Vision · MediaPipe · OpenCV</div>
          <p style="font-size:14px;margin-bottom:14px">
            Upload a badminton training video and get instant pose overlay,
            stroke detection, landing-point distribution, and joint-angle time series.
            Supports side-by-side comparison of two videos to benchmark technique.
          </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.page_link("pages/1_Pose_Recognition.py", label="Open Pose Recognition Tool →", icon="🎯")

with c2:
    st.markdown(
        """
        <div class="tool-card">
          <div style="font-size:22px;margin-bottom:6px">🏸 羽毛球拍用户意见挖掘</div>
          <div style="color:#66727f;font-size:13px;margin-bottom:12px">LLM · Bilibili Crawler · VOC Analysis</div>
          <p style="font-size:14px;margin-bottom:14px">
            Enter a racket model name and the tool automatically collects danmaku and
            comments from Bilibili, then uses a large language model to extract structured
            user opinions — needs, pain points, purchase drivers — with evidence links back
            to the original videos.
          </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.page_link("pages/2_VOC.py", label="Open VOC Mining Tool →", icon="🏸")

# ── Contact ───────────────────────────────────────────────────────────────────
st.markdown('<div class="section-title">Contact</div>', unsafe_allow_html=True)
st.markdown(
    "📧 [smalldatamatrix@gmail.com](mailto:smalldatamatrix@gmail.com) &nbsp;·&nbsp; "
    "🐙 [github.com/SmallDataMatrix](https://github.com/SmallDataMatrix)"
)
