import base64
import streamlit as st
from pathlib import Path

st.set_page_config(
    page_title="王可心 · 简历",
    page_icon="HY",
    layout="wide",
    initial_sidebar_state="expanded",
)

_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500&display=swap');

:root {
  --canvas:    #F9FAFB;
  --surface:   #FFFFFF;
  --ink:       #18181B;
  --secondary: #71717A;
  --muted:     #94A3B8;
  --accent:    #3B82F6;
  --border:    rgba(226,232,240,0.7);
  --shadow:    0 20px 48px -16px rgba(0,0,0,0.06);
}

html, body, [class*="css"], p, span, div, h1, h2, h3, h4 {
  font-family: 'Outfit', 'Helvetica Neue', system-ui, sans-serif !important;
}

#MainMenu, footer { visibility: hidden; }
.stAppDeployButton { display: none; }
header[data-testid="stHeader"] { background: transparent; }
.stApp { background: var(--canvas); }
.main .block-container {
  max-width: 960px;
  padding: 0 2rem 6rem;
  margin: 0 auto;
}

@keyframes fadeUp {
  from { opacity: 0; transform: translateY(18px); }
  to   { opacity: 1; transform: translateY(0); }
}
.fu { animation: fadeUp 0.65s cubic-bezier(0.16,1,0.3,1) both; }
.d1 { animation-delay: 0.08s; }
.d2 { animation-delay: 0.18s; }

.cv-header { padding: 5rem 0 2rem; }
.eyebrow {
  font-family: 'JetBrains Mono', monospace !important;
  font-size: 11px;
  font-weight: 500;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--accent);
}
.display-name {
  font-size: clamp(2.25rem, 5vw, 3.5rem);
  font-weight: 800;
  letter-spacing: -0.04em;
  line-height: 1.05;
  color: var(--ink);
  margin: 0.5rem 0 0.5rem;
}
.cv-sub {
  font-size: 0.95rem;
  color: var(--secondary);
}

.pdf-wrap {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 14px;
  overflow: hidden;
  box-shadow: var(--shadow);
  margin-top: 1.5rem;
}

a.page-link {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 13px;
  font-weight: 600;
  color: var(--accent);
  text-decoration: none;
  letter-spacing: 0.01em;
  transition: gap 0.2s;
  margin-top: 1.5rem;
}
a.page-link:hover { gap: 10px; }
</style>
"""

st.markdown(_CSS, unsafe_allow_html=True)

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown(
    """
    <div class="cv-header">
      <div class="eyebrow fu">简历</div>
      <div class="display-name fu d1">王可心</div>
      <div class="cv-sub fu d2">Kexin Wang &nbsp;&middot;&nbsp; 数据科学家 / 独立顾问</div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── PDF Embed ─────────────────────────────────────────────────────────────────
pdf_path = Path(__file__).parent.parent / "data" / "Kexin_Wang_CV_CN.pdf"

if pdf_path.exists():
    pdf_bytes = pdf_path.read_bytes()
    b64 = base64.b64encode(pdf_bytes).decode()
    # Chrome blocks data: URI iframes for PDFs; use a blob URL created via JS instead.
    blob_viewer = f"""
    <!DOCTYPE html>
    <html>
    <head><style>
      body {{ margin: 0; padding: 0; background: #fff; }}
      iframe {{ width: 100%; height: 960px; border: none; display: block; }}
    </style></head>
    <body>
    <iframe id="pdf-frame"></iframe>
    <script>
      const b64 = "{b64}";
      const binary = atob(b64);
      const bytes = new Uint8Array(binary.length);
      for (let i = 0; i < binary.length; i++) {{ bytes[i] = binary.charCodeAt(i); }}
      const blob = new Blob([bytes], {{ type: "application/pdf" }});
      document.getElementById("pdf-frame").src = URL.createObjectURL(blob);
    </script>
    </body></html>
    """
    import streamlit.components.v1 as components
    components.html(blob_viewer, height=960, scrolling=False)

    col, _ = st.columns([1, 3])
    with col:
        st.download_button(
            label="下载简历 PDF",
            data=pdf_bytes,
            file_name="Kexin_Wang_CV.pdf",
            mime="application/pdf",
        )
else:
    st.error("简历 PDF 文件未找到。")

st.markdown('<a class="page-link fu" href="/" target="_self">返回求职信 →</a>', unsafe_allow_html=True)
