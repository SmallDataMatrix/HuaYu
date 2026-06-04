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
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500&family=Noto+Sans+SC:wght@300;400;500;700&display=swap');

:root {
  --canvas:    #F9FAFB;
  --surface:   #FFFFFF;
  --ink:       #18181B;
  --secondary: #71717A;
  --muted:     #94A3B8;
  --accent:    #3B82F6;
  --accent-bg: #EFF6FF;
  --border:    rgba(226,232,240,0.8);
  --shadow:    0 20px 48px -16px rgba(0,0,0,0.07);
}

html, body, [class*="css"], p, span, div, h1, h2, h3, h4 {
  font-family: 'Outfit', 'Noto Sans SC', 'Helvetica Neue', system-ui, sans-serif !important;
}

#MainMenu, footer { visibility: hidden; }
.stAppDeployButton { display: none; }
header[data-testid="stHeader"] { background: transparent; }
.stApp { background: var(--canvas); }
.main .block-container {
  max-width: 900px;
  padding: 0 2rem 6rem;
  margin: 0 auto;
}

@keyframes fadeUp {
  from { opacity: 0; transform: translateY(16px); }
  to   { opacity: 1; transform: translateY(0); }
}
.fu  { animation: fadeUp 0.6s cubic-bezier(0.16,1,0.3,1) both; }
.d1  { animation-delay: 0.06s; }
.d2  { animation-delay: 0.14s; }
.d3  { animation-delay: 0.22s; }
.d4  { animation-delay: 0.30s; }

/* ── CV CARD ── */
.cv-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 20px;
  box-shadow: var(--shadow);
  overflow: hidden;
  margin-top: 3.5rem;
}

/* ── HEADER BAND ── */
.cv-header {
  display: flex;
  align-items: center;
  gap: 2.4rem;
  padding: 2.8rem 3rem 2.4rem;
  background: linear-gradient(135deg, #1e3a5f 0%, #2563EB 100%);
  color: #fff;
}
.cv-photo {
  width: 110px;
  height: 110px;
  border-radius: 50%;
  object-fit: cover;
  object-position: center top;
  border: 3px solid rgba(255,255,255,0.35);
  flex-shrink: 0;
}
.cv-photo-placeholder {
  width: 110px; height: 110px; border-radius: 50%;
  background: rgba(255,255,255,0.15);
  border: 3px solid rgba(255,255,255,0.3);
  display: flex; align-items: center; justify-content: center;
  font-size: 2.5rem; flex-shrink: 0;
}
.cv-name {
  font-size: 2.2rem;
  font-weight: 800;
  letter-spacing: -0.04em;
  line-height: 1.1;
  color: #fff;
}
.cv-title {
  font-size: 0.95rem;
  font-weight: 400;
  color: rgba(255,255,255,0.75);
  margin-top: 0.35rem;
  font-family: 'JetBrains Mono', monospace !important;
  letter-spacing: 0.04em;
}
.cv-contacts {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem 1.6rem;
  margin-top: 1rem;
}
.cv-contacts a, .cv-contact-item {
  font-size: 13px;
  color: rgba(255,255,255,0.82);
  text-decoration: none;
  display: flex;
  align-items: center;
  gap: 5px;
}
.cv-contacts a:hover { color: #fff; }

/* ── BODY LAYOUT ── */
.cv-body {
  display: grid;
  grid-template-columns: 260px 1fr;
  gap: 0;
}
.cv-left {
  padding: 2.4rem 2rem 2.4rem 3rem;
  border-right: 1px solid var(--border);
}
.cv-right {
  padding: 2.4rem 3rem 2.4rem 2.4rem;
}

/* ── SECTION LABEL ── */
.sec-label {
  font-family: 'JetBrains Mono', monospace !important;
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--accent);
  margin: 0 0 1rem;
  padding-bottom: 0.55rem;
  border-bottom: 1px solid var(--border);
}

/* ── SUMMARY ── */
.summary-text {
  font-family: 'Noto Sans SC', sans-serif !important;
  font-size: 13.5px;
  color: var(--secondary);
  line-height: 2;
}

/* ── EDUCATION ── */
.edu-item { margin-bottom: 1.4rem; }
.edu-deg  {
  font-size: 13.5px;
  font-weight: 700;
  color: var(--ink);
  line-height: 1.4;
}
.edu-school {
  font-family: 'Noto Sans SC', sans-serif !important;
  font-size: 12.5px;
  color: var(--secondary);
  margin-top: 0.2rem;
}
.edu-date {
  font-family: 'JetBrains Mono', monospace !important;
  font-size: 10.5px;
  color: var(--muted);
  margin-top: 0.25rem;
  letter-spacing: 0.04em;
}

/* ── SKILLS ── */
.skill-group { margin-bottom: 1.1rem; }
.skill-group-name {
  font-size: 11px;
  font-weight: 700;
  color: var(--ink);
  letter-spacing: 0.06em;
  text-transform: uppercase;
  margin-bottom: 0.45rem;
}
.skill-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
}
.skill-tag {
  font-family: 'JetBrains Mono', monospace !important;
  font-size: 10.5px;
  background: var(--accent-bg);
  color: var(--accent);
  border-radius: 5px;
  padding: 2px 8px;
  font-weight: 500;
}

/* ── EXPERIENCE TIMELINE ── */
.exp-item { position: relative; padding-left: 1.2rem; margin-bottom: 2rem; }
.exp-item::before {
  content: '';
  position: absolute;
  left: 0; top: 7px;
  width: 7px; height: 7px;
  background: var(--accent);
  border-radius: 50%;
}
.exp-item::after {
  content: '';
  position: absolute;
  left: 3px; top: 18px; bottom: -1rem;
  width: 1px;
  background: var(--border);
}
.exp-item:last-child::after { display: none; }
.exp-date {
  font-family: 'JetBrains Mono', monospace !important;
  font-size: 10.5px;
  color: var(--muted);
  letter-spacing: 0.05em;
  margin-bottom: 0.25rem;
}
.exp-role {
  font-size: 14.5px;
  font-weight: 700;
  color: var(--ink);
  letter-spacing: -0.02em;
  line-height: 1.3;
}
.exp-company {
  font-size: 12.5px;
  color: var(--accent);
  font-weight: 600;
  margin-top: 0.15rem;
  margin-bottom: 0.65rem;
}
.exp-bullets {
  font-family: 'Noto Sans SC', sans-serif !important;
  font-size: 12.5px;
  color: var(--secondary);
  line-height: 1.9;
  padding-left: 1.1rem;
}
.exp-bullets li { margin-bottom: 0.2rem; }
.exp-break {
  font-family: 'Noto Sans SC', sans-serif !important;
  font-size: 12.5px;
  color: var(--muted);
  font-style: italic;
  margin-top: 0.3rem;
}

/* ── BACK LINK ── */
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
  margin-top: 2rem;
  margin-bottom: 1rem;
}
a.page-link:hover { gap: 10px; }

@media (max-width: 640px) {
  .cv-body { grid-template-columns: 1fr; }
  .cv-left { border-right: none; border-bottom: 1px solid var(--border); padding: 2rem; }
  .cv-right { padding: 2rem; }
  .cv-header { flex-direction: column; align-items: flex-start; padding: 2rem; }
}
</style>
"""

st.markdown(_CSS, unsafe_allow_html=True)

# ── Photo ─────────────────────────────────────────────────────────────────────
photo_path = Path(__file__).parent.parent / "data" / "Kexin_Wang_CV_photo.png"
photo_tag = '<div class="cv-photo-placeholder">👤</div>'
if photo_path.exists():
    photo_b64 = base64.b64encode(photo_path.read_bytes()).decode()
    photo_tag = f'<img class="cv-photo" src="data:image/png;base64,{photo_b64}" alt="王可心">'

# ── CV HTML ───────────────────────────────────────────────────────────────────
cv_html = f"""
<div class="cv-card fu">

  <!-- HEADER -->
  <div class="cv-header">
    {photo_tag}
    <div>
      <div class="cv-name">王可心</div>
      <div class="cv-title">Senior Data Scientist &nbsp;/&nbsp; Independent Consultant</div>
      <div class="cv-contacts">
        <a href="tel:+8615601035571">📱 (+86) 156-0103-5571</a>
        <a href="mailto:smalldatamatrix@gmail.com">✉️ smalldatamatrix@gmail.com</a>
        <a href="https://fsquaredquant.nl/about-us//" target="_blank" rel="noreferrer">⌨️ FFquant</a>
      </div>
    </div>
  </div>

  <!-- BODY -->
  <div class="cv-body">

    <!-- LEFT PANEL -->
    <div class="cv-left">

      <div class="sec-label">关于我</div>
      <p class="summary-text">
        资深数据科学家，在金融、医疗、零售及数字产品领域拥有丰富的 AI 与机器学习落地经验。
        擅长深度学习、NLP、全栈 AI 产品开发及端到端数据管道构建，能将复杂数据挑战转化为可扩展、
        面向业务的实际解决方案。
      </p>

      <div class="sec-label" style="margin-top:2rem;">教育经历</div>

      <div class="edu-item">
        <div class="edu-deg">生物医学工程 &nbsp;硕士</div>
        <div class="edu-school">荷兰格罗宁根大学</div>
        <div class="edu-date">2012.09 – 2014.08</div>
      </div>
      <div class="edu-item">
        <div class="edu-deg">生物医学工程 &nbsp;本科</div>
        <div class="edu-school">北京工业大学</div>
        <div class="edu-date">2006.09 – 2010.08</div>
      </div>

      <div class="sec-label" style="margin-top:2rem;">技术栈</div>

      <div class="skill-group">
        <div class="skill-group-name">ML / DL</div>
        <div class="skill-tags">
          <span class="skill-tag">PyTorch</span>
          <span class="skill-tag">Keras</span>
          <span class="skill-tag">LSTM</span>
          <span class="skill-tag">Transformers</span>
          <span class="skill-tag">LoRA</span>
          <span class="skill-tag">MediaPipe</span>
        </div>
      </div>
      <div class="skill-group">
        <div class="skill-group-name">数据 / 工程</div>
        <div class="skill-tags">
          <span class="skill-tag">Python</span>
          <span class="skill-tag">PySpark</span>
          <span class="skill-tag">SQL</span>
          <span class="skill-tag">FastAPI</span>
          <span class="skill-tag">Streamlit</span>
          <span class="skill-tag">Pandas</span>
        </div>
      </div>
      <div class="skill-group">
        <div class="skill-group-name">平台 / 云</div>
        <div class="skill-tags">
          <span class="skill-tag">Azure</span>
          <span class="skill-tag">Kubernetes</span>
          <span class="skill-tag">Docker</span>
          <span class="skill-tag">Dash</span>
        </div>
      </div>
      <div class="skill-group">
        <div class="skill-group-name">NLP / LLM</div>
        <div class="skill-tags">
          <span class="skill-tag">OpenAI</span>
          <span class="skill-tag">Qwen2.5</span>
          <span class="skill-tag">DeBERTa</span>
          <span class="skill-tag">LangChain</span>
        </div>
      </div>

      <div class="sec-label" style="margin-top:2rem;">语言</div>
      <div class="skill-tags">
        <span class="skill-tag">普通话（母语）</span>
        <span class="skill-tag">英语（流利）</span>
        <span class="skill-tag">荷兰语（基础）</span>
      </div>

    </div>

    <!-- RIGHT PANEL -->
    <div class="cv-right">

      <div class="sec-label">工作经历</div>

      <div class="exp-item">
        <div class="exp-date">2025.10 — 至今</div>
        <div class="exp-role">资深数据科学家</div>
        <div class="exp-company">Flux B.V. &nbsp;·&nbsp; 荷兰，阿姆斯特丹</div>
        <ul class="exp-bullets">
          <li>构建端到端 AI/ML 合规评分平台，结合机器学习、规则引擎与业务逻辑，用于评估记录质量、检测异常并支持基于风险的决策。</li>
          <li>开发覆盖前端、后端及数据库层的全栈功能，包括评分 API、数据管道、持久化存储及可交互合规仪表盘。</li>
          <li>验证模型性能、提升系统可靠性，记录评分方法论并支持面向业务用户的可扩展生产部署。</li>
        </ul>
      </div>

      <div class="exp-item">
        <div class="exp-date">2023.06 — 2024.12</div>
        <div class="exp-role">Kaggle 全球数据科学竞赛</div>
        <div class="exp-company">3 枚奖牌 &nbsp;·&nbsp; 独立参赛</div>
        <ul class="exp-bullets">
          <li><b>银牌</b> · Eedi 数学学习误区挖掘（2024.12）—— 使用 Qwen2.5 + LoRA 通过检索最相关错误答案识别学生学习误区。</li>
          <li><b>银牌</b> · 2023 图像匹配挑战赛 —— 使用 SuperPoint + SuperGlue 从 2D 图像重建 3D 场景。</li>
          <li><b>铜牌</b> · Google 孤立手语识别 —— 基于 MediaPipe Holistic 提取 3D 坐标，开发 DeBERTa 风格手势识别模型。</li>
        </ul>
      </div>

      <div class="exp-item">
        <div class="exp-date">2022.09 — 2024.11</div>
        <div class="exp-role">联合创始人 · AI 技术团队</div>
        <div class="exp-company">Aistheticinteriors &nbsp;·&nbsp; 荷兰，阿姆斯特丹</div>
        <ul class="exp-bullets">
          <li>为客户量身定制室内设计算法并优化 AI 模型，确保工具契合细分市场需求。</li>
          <li>设计并构建可扩展、高可用的云基础设施，以可接受成本托管 AI 驱动的室内设计工具。</li>
        </ul>
      </div>

      <div class="exp-item">
        <div class="exp-date">2022.01 — 2022.09</div>
        <div class="exp-role">资深数据科学家</div>
        <div class="exp-company">葛兰素史克 (GSK) &nbsp;·&nbsp; 中国，上海</div>
        <ul class="exp-bullets">
          <li>开发营销分析框架（CRM/RMF），量化业务影响，通过客户细分诊断市场问题并生成洞察。</li>
          <li>构建联邦学习 CTR 广告增长预测模型，优化整体增长表现及渠道投资。</li>
          <li>发起基于个人健康数据的定制化营养产品推荐项目。</li>
        </ul>
      </div>

      <div class="exp-item">
        <div class="exp-date">2020.07 — 2021.12</div>
        <div class="exp-role">资深数据科学家</div>
        <div class="exp-company">菲利普·莫里斯国际 (PMI) &nbsp;·&nbsp; 荷兰，阿姆斯特丹</div>
        <ul class="exp-bullets">
          <li>设计基于 LSTM 的定量定价模型，预测各地区零售量，平均准确率达 95%。</li>
          <li>构建 Dash/Kubernetes 网页分析应用，实现区域零售量预测与市场趋势实时可视化，支持交互式数据探索。</li>
        </ul>
      </div>

      <div class="exp-item">
        <div class="exp-date">2018.07 — 2020.07</div>
        <div class="exp-role">风险模型工程师</div>
        <div class="exp-company">荷兰合作银行 (Rabobank) &nbsp;·&nbsp; 荷兰，乌得勒支</div>
        <ul class="exp-bullets">
          <li>参与涉及逾 1000 亿欧元资产的风险模型方法论决策，与内部利益相关方深度协作。</li>
          <li>主导信用/资产负债管理风险模型的 Python 实现；基于 Azure DevOps 构建 Python 软件解决方案。</li>
          <li>指导初级同事搭建 Python 信用风险建模库，识别信用风险模型的适当风险驱动因素。</li>
        </ul>
      </div>

      <div class="exp-item">
        <div class="exp-date">2014.09 — 2018.06</div>
        <div class="exp-role">数据科学家</div>
        <div class="exp-company">荷兰 ING 集团 &nbsp;·&nbsp; 荷兰，阿姆斯特丹</div>
        <ul class="exp-bullets">
          <li>为 ING 创新个人财务管理应用 Yolt（2017 年英国最佳 PFM 工具）从零构建多国 ML 模型（PySpark）。</li>
          <li>基于历史银行数据，使用聚类 + LSTM 预测客户未来交易；以前馈神经网络（Keras）进行交易分类。</li>
          <li>构建字段分解机算法库（PySpark + C++），训练 ING 广告推荐系统，将点击率提升约 80%。</li>
          <li>开发 BeautifulSoup 网页爬虫获取英国商户信息；利用自编码器对 Webtrekk 数据进行用户流失预测。</li>
        </ul>
      </div>

      <div class="exp-item">
        <div class="exp-date">2014.01 — 2014.08</div>
        <div class="exp-role">硕士论文研究</div>
        <div class="exp-company">格罗宁根大学医学中心 (UMCG) &nbsp;·&nbsp; 荷兰，格罗宁根</div>
        <ul class="exp-bullets">
          <li>对 fMRI 数据进行分析并构建结构化曲线，使用 PCA、SVM、聚类算法对不同类型帕金森病进行分类。</li>
        </ul>
      </div>

      <div class="exp-item">
        <div class="exp-date">2013.04 — 2013.09</div>
        <div class="exp-role">实习生</div>
        <div class="exp-company">代尔夫特理工大学 (TU Delft) &nbsp;·&nbsp; 荷兰，代尔夫特</div>
        <ul class="exp-bullets">
          <li>通过 Arduino + VB 为代尔夫特钩形假肢设计数据采集系统，进行情景分析，显著改善用户体验与产品效率。</li>
        </ul>
      </div>

      <div class="exp-item">
        <div class="exp-date">2025.01 — 2025.10</div>
        <div class="exp-role">间隔年</div>
        <div class="exp-break">环球旅行 · 羽毛球 · 摄影</div>
      </div>

    </div>
  </div>
</div>
"""

# Streamlit runs HTML through a Markdown parser: 4-space indentation becomes a
# code block and blank lines split the block into <p> fragments. Strip leading
# whitespace and drop blank lines so it renders as raw HTML.
cv_html = "\n".join(line.strip() for line in cv_html.splitlines() if line.strip())
st.markdown(cv_html, unsafe_allow_html=True)

st.markdown('<a class="page-link fu" href="/" target="_self">← 返回求职信</a>', unsafe_allow_html=True)
