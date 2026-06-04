import streamlit as st

st.set_page_config(
    page_title="Hua Yu · Data Scientist",
    page_icon="HY",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Global styles ──────────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500&display=swap');

    :root {
      --canvas:      #F9FAFB;
      --surface:     #FFFFFF;
      --ink:         #18181B;
      --secondary:   #71717A;
      --muted:       #94A3B8;
      --accent:      #3B82F6;
      --accent-bg:   #EFF6FF;
      --border:      rgba(226,232,240,0.7);
      --shadow:      0 20px 48px -16px rgba(0,0,0,0.06);
    }

    html, body, [class*="css"], p, span, div, h1, h2, h3, h4 {
      font-family: 'Outfit', 'Helvetica Neue', system-ui, sans-serif !important;
    }

    /* Hide Streamlit chrome */
    #MainMenu, footer { visibility: hidden; }
    .stAppDeployButton { display: none; }
    [data-testid="stSidebarNav"] { display: none; }
    header[data-testid="stHeader"] { background: transparent; }

    /* Canvas */
    .stApp { background: var(--canvas); }
    .main .block-container {
      max-width: 1080px;
      padding: 0 2rem 6rem;
      margin: 0 auto;
    }

    /* Fade-up reveal */
    @keyframes fadeUp {
      from { opacity: 0; transform: translateY(18px); }
      to   { opacity: 1; transform: translateY(0); }
    }
    .fu  { animation: fadeUp 0.65s cubic-bezier(0.16,1,0.3,1) both; }
    .d1  { animation-delay: 0.08s; }
    .d2  { animation-delay: 0.18s; }
    .d3  { animation-delay: 0.28s; }
    .d4  { animation-delay: 0.38s; }
    .d5  { animation-delay: 0.48s; }

    /* ── HERO ──────────────────────────────────────────────────────────── */
    .hero { padding: 5.5rem 0 0; }

    .eyebrow {
      font-family: 'JetBrains Mono', monospace !important;
      font-size: 11px;
      font-weight: 500;
      letter-spacing: 0.14em;
      text-transform: uppercase;
      color: var(--accent);
    }

    .display-name {
      font-size: clamp(2.75rem, 6vw, 4.25rem);
      font-weight: 800;
      letter-spacing: -0.04em;
      line-height: 1.0;
      color: var(--ink);
      margin: 0.5rem 0 1.1rem;
    }

    .role-line {
      font-size: 1.05rem;
      font-weight: 400;
      color: var(--secondary);
      line-height: 1.7;
      max-width: 540px;
    }

    .chips {
      display: flex;
      flex-wrap: wrap;
      gap: 7px;
      margin-top: 1.75rem;
    }
    .chip {
      font-family: 'JetBrains Mono', monospace !important;
      font-size: 10.5px;
      font-weight: 500;
      letter-spacing: 0.04em;
      color: var(--secondary);
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 6px;
      padding: 4px 11px;
    }

    /* ── SECTION DIVIDER ─────────────────────────────────────────────── */
    .section-label {
      display: flex;
      align-items: center;
      gap: 14px;
      margin: 4.5rem 0 1.75rem;
    }
    .section-label span {
      font-family: 'JetBrains Mono', monospace !important;
      font-size: 10.5px;
      font-weight: 600;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      color: var(--muted);
      white-space: nowrap;
    }
    .section-label::after {
      content: '';
      flex: 1;
      height: 1px;
      background: var(--border);
    }

    /* ── SKILLS BENTO ────────────────────────────────────────────────── */
    .skills-grid {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 1px;
      background: var(--border);
      border: 1px solid var(--border);
      border-radius: 14px;
      overflow: hidden;
    }
    .skill-cell {
      background: var(--surface);
      padding: 1.4rem 1.6rem;
    }
    .skill-cell-label {
      font-family: 'JetBrains Mono', monospace !important;
      font-size: 10px;
      font-weight: 600;
      letter-spacing: 0.1em;
      text-transform: uppercase;
      color: var(--muted);
      margin-bottom: 0.8rem;
    }
    .skill-row {
      font-size: 13px;
      color: var(--secondary);
      line-height: 2.05;
    }

    /* ── PROJECT CARDS ───────────────────────────────────────────────── */
    .project-card {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 16px;
      padding: 2rem 2.1rem 1.6rem;
      box-shadow: var(--shadow);
      position: relative;
      overflow: hidden;
      height: 100%;
      transition: border-color 0.25s ease, box-shadow 0.25s ease;
    }
    .project-card::after {
      content: '';
      position: absolute;
      inset: 0 0 auto;
      height: 3px;
      background: linear-gradient(90deg, var(--accent), rgba(59,130,246,0.3));
      opacity: 0;
      transition: opacity 0.25s ease;
    }
    .project-card:hover {
      border-color: rgba(59,130,246,0.3);
      box-shadow: 0 28px 56px -18px rgba(59,130,246,0.14);
    }
    .project-card:hover::after { opacity: 1; }

    .project-tag {
      display: inline-block;
      font-family: 'JetBrains Mono', monospace !important;
      font-size: 10px;
      font-weight: 500;
      letter-spacing: 0.07em;
      text-transform: uppercase;
      color: var(--accent);
      background: var(--accent-bg);
      border-radius: 5px;
      padding: 3px 9px;
      margin-bottom: 1rem;
    }
    .project-title {
      font-size: 1.2rem;
      font-weight: 700;
      letter-spacing: -0.025em;
      color: var(--ink);
      line-height: 1.25;
      margin-bottom: 0.6rem;
    }
    .project-desc {
      font-size: 13.5px;
      color: var(--secondary);
      line-height: 1.7;
    }
    .tech-row {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      margin-top: 1.25rem;
    }
    .tech-pill {
      font-family: 'JetBrains Mono', monospace !important;
      font-size: 10px;
      color: var(--muted);
      background: var(--canvas);
      border: 1px solid var(--border);
      border-radius: 4px;
      padding: 2px 8px;
    }

    /* page_link overrides */
    [data-testid="stPageLink"] { margin-top: 1.25rem; }
    [data-testid="stPageLink"] a {
      display: inline-flex !important;
      align-items: center !important;
      gap: 5px !important;
      font-size: 13px !important;
      font-weight: 600 !important;
      color: var(--accent) !important;
      text-decoration: none !important;
      letter-spacing: 0.01em !important;
      transition: gap 0.2s !important;
    }
    [data-testid="stPageLink"] a:hover { gap: 10px !important; }

    /* ── CONTACT BAR ──────────────────────────────────────────────────── */
    .contact-bar {
      display: flex;
      flex-wrap: wrap;
      gap: 28px;
      align-items: center;
      padding: 1.4rem 2rem;
      margin-top: 4rem;
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 12px;
    }
    .contact-bar a {
      font-size: 13.5px;
      font-weight: 500;
      color: var(--secondary);
      text-decoration: none;
      display: flex;
      align-items: center;
      gap: 7px;
      transition: color 0.15s;
    }
    .contact-bar a:hover { color: var(--accent); }
    .contact-dot {
      width: 4px; height: 4px;
      background: var(--border);
      border-radius: 50%;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── Hero ───────────────────────────────────────────────────────────────────────
st.markdown(
    """
    <div class="hero">
      <div class="eyebrow fu">Portfolio &nbsp;/&nbsp; Data Scientist</div>
      <div class="display-name fu d1">Hua Yu</div>
      <div class="role-line fu d2">
        Building practical ML systems that extract signal from messy data —
        from real-time computer vision for sports analytics to large-language-model
        pipelines that surface user insights at scale.
      </div>
      <div class="chips fu d3">
        <span class="chip">Python</span>
        <span class="chip">Machine Learning</span>
        <span class="chip">Computer Vision</span>
        <span class="chip">LLM / NLP</span>
        <span class="chip">Streamlit</span>
        <span class="chip">FastAPI</span>
        <span class="chip">MediaPipe</span>
        <span class="chip">Data Visualization</span>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── Skills ─────────────────────────────────────────────────────────────────────
st.markdown(
    """
    <div class="section-label fu d4"><span>Skills</span></div>
    <div class="skills-grid fu d4">
      <div class="skill-cell">
        <div class="skill-cell-label">Data &amp; ML</div>
        <div class="skill-row">Pandas &middot; NumPy</div>
        <div class="skill-row">Scikit-learn &middot; PyTorch</div>
        <div class="skill-row">JAX &middot; MediaPipe</div>
        <div class="skill-row">OpenCV &middot; SQL</div>
      </div>
      <div class="skill-cell">
        <div class="skill-cell-label">LLM &amp; NLP</div>
        <div class="skill-row">Prompt engineering</div>
        <div class="skill-row">DeepSeek / OpenAI API</div>
        <div class="skill-row">Opinion mining (VOC)</div>
        <div class="skill-row">RAG pipelines</div>
      </div>
      <div class="skill-cell">
        <div class="skill-cell-label">Engineering</div>
        <div class="skill-row">Streamlit &middot; FastAPI</div>
        <div class="skill-row">Docker &middot; GitHub Actions</div>
        <div class="skill-row">REST API design</div>
        <div class="skill-row">Python packaging</div>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── Projects ───────────────────────────────────────────────────────────────────
st.markdown(
    '<div class="section-label fu d5"><span>Projects</span></div>',
    unsafe_allow_html=True,
)

col_left, col_right = st.columns([3, 2], gap="large")

with col_left:
    st.markdown(
        """
        <div class="project-card fu">
          <div class="project-tag">Computer Vision</div>
          <div class="project-title">Badminton Training Analyzer</div>
          <div class="project-desc">
            Upload a training video and get an instant pose-skeleton overlay,
            stroke-by-stroke detection table, court landing-point heatmap, and
            joint-angle time series. Supports side-by-side comparison of two videos
            to benchmark technique changes over time.
          </div>
          <div class="tech-row">
            <span class="tech-pill">MediaPipe</span>
            <span class="tech-pill">OpenCV</span>
            <span class="tech-pill">Matplotlib</span>
            <span class="tech-pill">Pandas</span>
            <span class="tech-pill">NumPy</span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.page_link("pages/1_Pose_Recognition.py", label="Open Pose Recognition Tool  →")

with col_right:
    st.markdown(
        """
        <div class="project-card fu">
          <div class="project-tag">LLM &middot; Web Crawling</div>
          <div class="project-title">Racket VOC Mining</div>
          <div class="project-desc">
            Enter a racket model name. The tool crawls Bilibili danmaku and comments,
            then runs a map-reduce LLM pipeline to produce a structured voice-of-customer
            report: needs, pain points, purchase drivers, and competitor comparisons —
            every finding linked back to its source video.
          </div>
          <div class="tech-row">
            <span class="tech-pill">DeepSeek API</span>
            <span class="tech-pill">Bilibili Crawler</span>
            <span class="tech-pill">Map-Reduce</span>
            <span class="tech-pill">WBI Signing</span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.page_link("pages/2_VOC.py", label="Open VOC Mining Tool  →")

# ── Contact ────────────────────────────────────────────────────────────────────
st.markdown(
    """
    <div class="contact-bar fu">
      <a href="mailto:smalldatamatrix@gmail.com">
        smalldatamatrix@gmail.com
      </a>
      <div class="contact-dot"></div>
      <a href="https://github.com/SmallDataMatrix" target="_blank" rel="noreferrer">
        github.com/SmallDataMatrix
      </a>
    </div>
    """,
    unsafe_allow_html=True,
)
