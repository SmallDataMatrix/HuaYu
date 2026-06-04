import streamlit as st

st.set_page_config(
    page_title="王可心 · 华羽求职",
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
  --border:    rgba(226,232,240,0.7);
  --shadow:    0 20px 48px -16px rgba(0,0,0,0.06);
}

html, body, [class*="css"], p, span, div, h1, h2, h3, h4 {
  font-family: 'Outfit', 'Noto Sans SC', 'Helvetica Neue', system-ui, sans-serif !important;
}

#MainMenu, footer { visibility: hidden; }
.stAppDeployButton { display: none; }
header[data-testid="stHeader"] { background: transparent; }
.stApp { background: var(--canvas); }
.main .block-container {
  max-width: 820px;
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
.d3 { animation-delay: 0.28s; }
.d4 { animation-delay: 0.38s; }
.d5 { animation-delay: 0.48s; }

/* ── HERO ── */
.hero { padding: 5rem 0 0; }
.eyebrow {
  font-family: 'JetBrains Mono', monospace !important;
  font-size: 11px;
  font-weight: 500;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--accent);
}
.display-name {
  font-size: clamp(2.5rem, 6vw, 4rem);
  font-weight: 800;
  letter-spacing: -0.04em;
  line-height: 1.05;
  color: var(--ink);
  margin: 0.5rem 0 0.9rem;
}
.hero-sub {
  font-size: 0.95rem;
  color: var(--secondary);
  line-height: 1.6;
}

/* ── SECTION DIVIDER ── */
.section-label {
  display: flex;
  align-items: center;
  gap: 14px;
  margin: 3.75rem 0 1.5rem;
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

/* ── LETTER BODY ── */
.letter-para {
  font-family: 'Noto Sans SC', 'Outfit', sans-serif !important;
  font-size: 15.5px;
  color: var(--ink);
  line-height: 2.05;
  margin-bottom: 1.5rem;
  letter-spacing: 0.005em;
}

/* ── ROLE CALLOUT ── */
.role-callout {
  background: var(--accent-bg);
  border-left: 3px solid var(--accent);
  border-radius: 0 12px 12px 0;
  padding: 1.4rem 1.8rem;
  margin: 0.5rem 0 2rem;
}
.role-callout-label {
  font-family: 'JetBrains Mono', monospace !important;
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--accent);
  margin-bottom: 0.5rem;
}
.role-callout-title {
  font-size: 1.2rem;
  font-weight: 700;
  color: var(--ink);
  letter-spacing: -0.025em;
  margin-bottom: 0.5rem;
}
.role-callout-desc {
  font-family: 'Noto Sans SC', sans-serif !important;
  font-size: 14px;
  color: var(--secondary);
  line-height: 1.95;
}

/* ── INITIATIVE CARDS ── */
.initiative-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 16px;
  padding: 1.8rem 2rem 1.6rem;
  box-shadow: var(--shadow);
  margin-bottom: 1.25rem;
  position: relative;
  overflow: hidden;
}
.initiative-card::after {
  content: '';
  position: absolute;
  inset: 0 0 auto;
  height: 3px;
  background: linear-gradient(90deg, var(--accent), rgba(59,130,246,0.2));
}
.initiative-num {
  font-family: 'JetBrains Mono', monospace !important;
  font-size: 10.5px;
  font-weight: 600;
  letter-spacing: 0.14em;
  color: var(--accent);
  margin-bottom: 0.6rem;
}
.initiative-title {
  font-size: 1.1rem;
  font-weight: 700;
  color: var(--ink);
  letter-spacing: -0.025em;
  line-height: 1.35;
  margin-bottom: 0.9rem;
}
.initiative-body {
  font-family: 'Noto Sans SC', sans-serif !important;
  font-size: 14px;
  color: var(--secondary);
  line-height: 2.0;
}

/* ── STATS BENTO ── */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1px;
  background: var(--border);
  border: 1px solid var(--border);
  border-radius: 14px;
  overflow: hidden;
  margin: 1.5rem 0 2rem;
}
.stat-cell {
  background: var(--surface);
  padding: 1.35rem 1.6rem;
}
.stat-num {
  font-family: 'JetBrains Mono', monospace !important;
  font-size: 1.55rem;
  font-weight: 700;
  color: var(--ink);
  letter-spacing: -0.04em;
}
.stat-label {
  font-size: 12px;
  color: var(--muted);
  margin-top: 0.3rem;
  line-height: 1.5;
}

/* ── SIGNATURE ── */
.signature-block {
  margin-top: 2.5rem;
  padding-top: 2rem;
  border-top: 1px solid var(--border);
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  flex-wrap: wrap;
  gap: 1.25rem;
}
.signature-name {
  font-size: 1.35rem;
  font-weight: 700;
  color: var(--ink);
  letter-spacing: -0.03em;
}
.signature-meta {
  font-family: 'JetBrains Mono', monospace !important;
  font-size: 11px;
  color: var(--muted);
  margin-top: 0.4rem;
  line-height: 1.8;
}

/* ── PAGE LINK ── */
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
  margin-top: 0.6rem;
}
a.page-link:hover { gap: 10px; }

/* ── DEMO NOTE ── */
.demo-note {
  font-family: 'Noto Sans SC', sans-serif !important;
  font-size: 13px;
  color: var(--muted);
  margin: 0.75rem 0 0.1rem;
  font-style: italic;
}

/* ── CONTACT BAR ── */
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
.contact-dot { width: 4px; height: 4px; background: var(--border); border-radius: 50%; }
</style>
"""

st.markdown(_CSS, unsafe_allow_html=True)

# ── Hero ──────────────────────────────────────────────────────────────────────
st.markdown(
    """
    <div class="hero">
      <div class="eyebrow fu">求职信 &nbsp;/&nbsp; 华羽</div>
      <div class="display-name fu d1">致华羽</div>
      <div class="hero-sub fu d2">申请岗位：智能数据分析团队 Leader</div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── Opening & Ambition───────────────────────────────────────────────────────────────────
st.markdown('<div class="section-label fu d3"><span>初心 & 野心</span></div>', unsafe_allow_html=True)

st.markdown(
    """
    <div class="letter-para fu d3">各位华羽的朋友们好。</div>
    <div class="letter-para fu d3">
      羽毛球这条路，我走得不算远，球技也就是普通爱好者水平，这辈子大概摸不到专业的门槛。可我是真喜欢打球。
      能加入华羽，为自己喜欢的事认认真真花一份心思，这是我最朴素的初心。
    </div>
    <div class="letter-para fu d3">
      在数据科学这条路上，我倒是走了很多年。从实习生做到五百强企业的高级数据科学家，再到现在独立为企业做咨询和项目落地，
      这些年攒下来的技术底子，是我敢往前站一站的底气。
    </div>
    <div class="letter-para fu d3">
      这份初心，加上这份底气，让我生出了一个不算小的野心：我想用我的专业，陪着华羽，慢慢长成这个行业里真正的标杆。
      我盼着有一天，世界赛场上的顶尖选手手里握着的，是华羽的装备。到那时候，我也算是用另一种方式，跟世界顶级的高手们交过手了。
    </div>
    """,
    unsafe_allow_html=True,
)

# ── Role Proposal ─────────────────────────────────────────────────────────────
st.markdown('<div class="section-label fu d4"><span>申请角色</span></div>', unsafe_allow_html=True)

st.markdown(
    """
    <div class="fu d4">
      <div class="role-callout">
        <div class="role-callout-label">自定义岗位</div>
        <div class="role-callout-title">智能数据分析团队 Leader</div>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="letter-para fu d4">
      我想申请的不是华羽已经列出来的某一个现成岗位，而是一个华羽现在可能还没有，但我觉得最需要的角色，一个用数据科学，帮华羽把品牌做大的人。
      华羽真正的数据资产，不在公域有多少粉丝，而在那些完全属于自己的第一方交易和私域里。抖音和小红书的关注，
      说白了是租来的，用户数据归平台，我们能触达的深度非常有限。真正完全归华羽的金矿，是这三样东西：买过拍子进了微信私域的老客户、
      训练营的学员和家长、通过KOL优惠券下单后沉淀下来的真实用户。这些人的声音和行为，华羽能直接听到，能反复触达，不需要向任何平台交
      "数据租金"。我所有的工作，都会从这座真实拥有、规模虽小但能不断积累的矿开始。它不是最大的，但它是唯一谁也抢不走的。
    </div>
    """,
    unsafe_allow_html=True,
)

# ── Three Initiatives ─────────────────────────────────────────────────────────
st.markdown('<div class="section-label fu d5"><span>短期内想做的两件事</span></div>', unsafe_allow_html=True)

st.markdown(
    """
    <div class="letter-para fu d4">
    数据资产的价值，最终要落到两个决策上：做什么产品、不做什么产品。基于华羽现有的自有数据，从可操作的角度切入 我想在短期内（6-10个月）做以下两个基础项目。
    </div>
    <div class="initiative-card fu d5">
      <div class="initiative-num">01 &nbsp;&middot;&nbsp; 核心</div>
      <div class="initiative-title">用消费者真实的声音，驱动新品研发</div>
      <div class="initiative-body">
        小器材品牌最常见的死法，就是靠创始人的手感拍脑袋做新品，最后压一仓库卖不动的货。华羽现在积极研发新SKU，
        这个阶段最怕的不是广告投不准，而是产品定义本身就偏了。<br><br>
        我马上就能做的最小一步，是把华羽现有产品的电商评价，以及竞品同类产品的中差评都抓下来，做一轮情感分析和关键词归类，
        产出一份简报，告诉你这群人到底在在意什么，对手的产品在哪里被骂得最多。<br><br>
        数据不替人做决定，但它能保证做决定的人，不被直觉和一两个极端声音带偏。未来把它做成长期转动的引擎：定期从小红书、
        抖音、电商售后和微信群的对话里抓取声音，每个新品、每个季度自动产出研发参考，并在开模前加入对真实购买意愿的验证。
        这件事战略价值最高，也是我最愿意持续往里投精力的事。
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)
st.markdown('<p class="demo-note fu d5">我已经为这个想法做了一个小 demo，欢迎体验</p>', unsafe_allow_html=True)
st.markdown('<a class="page-link fu d5" href="/voc" target="_self">VOC 用户评价监测 →</a>', unsafe_allow_html=True)

st.markdown(
    """
    <div class="initiative-card fu d5">
      <div class="initiative-num">02 &nbsp;&middot;&nbsp; 增长</div>
      <div class="initiative-title">让广告费花得明白</div>
      <div class="initiative-body">
        用户声音告诉我们该主打什么卖点，KOL就按这个卖点去出内容，然后我去追踪这些内容到底带来了什么。
        做法不花哨，就是下笨功夫：给每个合作的KOL配专属优惠码，在平台允许的地方埋好带参数的链接，
        盯住他们内容发布前后品牌词的搜索量变化和店铺的进店增量，一点点拼成一张台账，粗估每个达人贡献的增量。<br><br>
        它和用户声音分析之间会形成一个不断修正的闭环：真实卖点 → KOL内容 → 转化数据 → 修正卖点，转着转着，
        就会长成一个对手很难抄走的增长引擎。这套东西，市面上通用的工具做不到，必须由一个懂数据的人从华羽自己的
        第一方数据里"养"出来。开始得越早，沉淀越厚，壁垒越深。
      </div>
    </div>

    <div class="initiative-card fu d5">
      <div class="initiative-num">03 &nbsp;&middot;&nbsp; 一点额外的辅助</div>
      <div class="initiative-title">给训练营做一点锦上添花的小事</div>
      <div class="initiative-body">
        我想做个小工具，教练给学员上课时拍一段动作视频，自动生成前后对比图。先不做复杂的自动标注和打分，
        只做并行对比和关键帧辅助，帮教练省点讲解的工夫，也让华羽的训练营多一个"有AI动作分析"的感知卖点。<br><br>
        我很清楚这件事离直接营收最远，所以绝不会让它占用最核心的精力。它是我对自己热爱的运动尽的一点心意，
        也是给培训体验加一个小小的分，仅此而已。
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)
st.markdown('<p class="demo-note fu d5">我已经为这个想法做了一个小 demo，欢迎体验</p>', unsafe_allow_html=True)
st.markdown('<a class="page-link fu d5" href="/pose_recognition" target="_self">辅助教学分析 Demo →</a>', unsafe_allow_html=True)

# ── Compensation ──────────────────────────────────────────────────────────────
st.markdown('<div class="section-label fu d5"><span>回报与风险对齐</span></div>', unsafe_allow_html=True)

st.markdown(
    """
    <div class="letter-para fu d5">
      我入行十多年了，温饱早就不成问题。我要的是一份象征性的底薪，加上跟品牌成长绑定的期权或分成。
      我把自己的回报，押在华羽能长多大上，而不是每个月固定发给我多少。
    </div>
    <div class="letter-para fu d5">
      同时，为了让华羽放心，我可以白纸黑字承诺：我写的每一行代码、搭建的每一条数据管线、产出的所有模型和文档，
      知识产权全部归属华羽，而且一定按方便交接的标准来做。哪一天我因为任何原因离开，接手的人不会被锁在一个黑箱外面，
      干瞪眼进不去。这样，创始人的风险和我个人的风险，是对齐的。
    </div>
    """,
    unsafe_allow_html=True,
)

# ── Background ────────────────────────────────────────────────────────────────
st.markdown('<div class="section-label fu d5"><span>背景经历</span></div>', unsafe_allow_html=True)

st.markdown(
    """
    <div class="stats-grid fu d5">
      <div class="stat-cell">
        <div class="stat-num">10+</div>
        <div class="stat-label">年数据科学<br>从业经验</div>
      </div>
      <div class="stat-cell">
        <div class="stat-num">4 家</div>
        <div class="stat-label">全球百强企业<br>数据科学家</div>
      </div>
      <div class="stat-cell">
        <div class="stat-num">3+ 全球奖牌</div>
        <div class="stat-label">Kaggle<br>全球数据科学竞赛多次获奖</div>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="letter-para fu d5">
      过去这十几年，我在 Rabobank 做过千亿资产的风控，在 ING 把广告推荐的点击率提升了大约 80%，在 GSK 做过客户分群。
      我干的一直不是拿现成工具套一套的活儿，而是把模糊的商业问题，先翻译成机器能解的数学问题，再做成跑在企业自有数据上的
      定制系统。这段经历给了我两样东西：一是把华羽那座小而独特的数据矿，真正炼成产品的能力；二是踩过足够多的坑，
      对"数据项目会怎么失败"有肌肉记忆。华羽现在不需要一个上来就大干快上、拿公司试错的科学家，
      它需要的是一个从一开始就分得清什么该做、什么不能做的人。我觉得，我恰好是适合现在这个阶段的那个人。
    </div>
    """,
    unsafe_allow_html=True,
)

# ── Closing ───────────────────────────────────────────────────────────────────
st.markdown(
    """
    <div class="letter-para fu d5">
      开头我提到的那点野心，是真的。我盼着有一天，世界顶级选手手里握着的，是华羽的装备。
      到那时候，我也算是用另一种方式，跟世界顶级高手们交过手了。
    </div>
    <div class="letter-para fu d5">
      但在此之前，我们得先把第一款被市场真正认可的产品做出来。我愿意从挖第一铲子开始，用数据和理性，陪着华羽走这段路。
    </div>
    """,
    unsafe_allow_html=True,
)

# ── Signature ─────────────────────────────────────────────────────────────────
st.markdown(
    """
    <div class="signature-block fu">
      <div>
        <div class="signature-name">王可心</div>
        <div class="signature-meta">Kexin Wang &nbsp;&middot;&nbsp; 数据科学顾问@FFquant<br>2026 年 6 月</div>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown('<a class="page-link fu" href="/cv" target="_self">查看完整简历 →</a>', unsafe_allow_html=True)

# ── Contact ───────────────────────────────────────────────────────────────────
st.markdown(
    """
    <div class="contact-bar fu">
      <a href="mailto:smalldatamatrix@gmail.com">smalldatamatrix@gmail.com</a>
      <div class="contact-dot"></div>
      <a href="https://fsquaredquant.nl/about-us//" target="_blank" rel="noreferrer">
        FFquant & Small Data Matrix
      </a>
    </div>
    """,
    unsafe_allow_html=True,
)
