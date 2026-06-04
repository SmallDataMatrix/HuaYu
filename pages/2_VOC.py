#！ python
# to run the app streamlit run app.py
import datetime
import logging
import time
import streamlit as st

from crawlers.bilibili import collect_corpus
from crawlers.bili_login import start_login, poll_login, verify_sessdata
from llm.voc import analyze
from storage import save_search, load_search, list_searches, delete_search, _slug

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(message)s",
    datefmt="%H:%M:%S",
)

st.set_page_config(page_title="羽毛球拍用户意见挖掘", page_icon="🏸", layout="wide")

# ── 免责声明横幅 ──────────────────────────────────────────────────────────────
st.markdown(
    '<div style="background:#fffbeb;border:1px solid #f59e0b;border-radius:8px;'
    'padding:8px 14px;margin-bottom:12px;font-size:12px;color:#92400e">'
    '⚠️ <b>仅供演示</b>：本工具为求职作品集演示项目，不以任何商业目的设计或运营，'
    '使用者须自行遵守相关法律法规，开发者不承担因不当使用所引发的任何法律责任。'
    '</div>',
    unsafe_allow_html=True,
)

st.title("🏸 羽毛球拍用户意见挖掘")
st.caption("基于 B 站弹幕与评论 · 大语言模型分析 · 挖掘用户真实诉求 · 每条结论可溯源原文")

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("设置")
    racket_name = st.text_input(
        "球拍名称", value="华羽屠夫",
        placeholder="例：李宁N90IV、尤尼克斯AX99",
    )
    run_btn = st.button("🔍 开始分析", use_container_width=True, type="primary")
    if st.button("🗑️ 清除会话缓存", use_container_width=True):
        for k in list(st.session_state.keys()):
            if k.startswith("voc_"):
                del st.session_state[k]
        st.success("会话缓存已清除（历史记录保留）")

    st.divider()

    # ── B站账号登录 ──────────────────────────────────────────────────────────
    st.markdown("**B站账号**")

    _sessdata = st.session_state.get("bili_sessdata")

    if _sessdata:
        # ── 已登录 ──────────────────────────────────────────────────────────
        uname = st.session_state.get("bili_uname", "B站用户")
        st.success(f"✅ 已登录：**{uname}**")
        st.caption("分析时将使用您的账号请求 B 站数据，获得更完整的评论。")
        if st.button("退出登录", use_container_width=True):
            for k in ("bili_sessdata", "bili_uname", "bili_qr"):
                st.session_state.pop(k, None)
            st.rerun()

    elif st.session_state.get("bili_qr"):
        # ── 正在扫码 ─────────────────────────────────────────────────────────
        qr = st.session_state.bili_qr
        result = poll_login(qr["key"], qr["cookies"])

        if result["status"] == "success" and result.get("sessdata"):
            with st.spinner("验证账号…"):
                uname = verify_sessdata(result["sessdata"])
            st.session_state.bili_sessdata = result["sessdata"]
            st.session_state.bili_uname = uname or "B站用户"
            st.session_state.pop("bili_qr", None)
            st.rerun()

        elif result["status"] == "expired":
            st.session_state.pop("bili_qr", None)
            st.error("二维码已过期，请重新生成")
            st.rerun()

        else:
            st.image(qr["img_bytes"], caption="用 B站 APP 扫描登录", use_container_width=True)
            if result["status"] == "scanned":
                st.info("✅ 已扫码，请在手机上点击「确认登录」")
            else:
                st.caption("打开 B站 APP → 右上角扫一扫")

            c1, c2 = st.columns(2)
            if c1.button("刷新状态", use_container_width=True):
                st.rerun()
            if c2.button("取消", use_container_width=True):
                st.session_state.pop("bili_qr", None)
                st.rerun()

            # Auto-poll: re-check every 2 s while QR is displayed
            time.sleep(2)
            st.rerun()

    else:
        # ── 未登录 ──────────────────────────────────────────────────────────
        st.info(
            "**匿名模式**（可正常使用）\n\n"
            "搜索最多 20 个候选视频，筛选后分析最相关的 **3 个**，"
            "每视频限 50 条评论，请求间隔较长。\n\n"
            "登录后：分析最相关 **5 个**视频，每视频 200 条评论。"
        )
        if st.button("🔑 扫码登录 B站（推荐）", use_container_width=True, type="primary"):
            with st.spinner("生成二维码…"):
                qr_data = start_login()
            if qr_data:
                st.session_state.bili_qr = qr_data
                st.rerun()
            else:
                st.error("二维码生成失败，请检查网络后重试")

    st.divider()
    st.markdown(
        "**数据说明**\n"
        "- 相关性过滤 + 播放量×时效排序\n"
        "- 弹幕含视频内精确时间戳\n"
        "- 每条结论可点击溯源到原始视频\n"
        "- 分析结果自动保存，重启后仍可查看"
    )

    # ── 历史记录 ──────────────────────────────────────────────────────────────
    st.divider()
    st.markdown("**📁 历史记录**")
    hist = list_searches()
    if not hist:
        st.caption("暂无历史记录")
    for m in hist:
        c1, c2 = st.columns([5, 1])
        label = f"{m['name']} · {m['saved_at'][5:10]} · {m['n_videos']}视频"
        if c1.button(label, key=f"hist_{m['slug']}", use_container_width=True):
            st.session_state["pending"] = {"name": m["name"], "force": False}
            st.rerun()
        if c2.button("🗑️", key=f"del_{m['slug']}"):
            delete_search(m["name"])
            st.session_state.pop(_cache_key(m["name"]), None)
            st.rerun()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _fmt_time(t: float | None) -> str | None:
    if t is None:
        return None
    m, s = divmod(int(t), 60)
    return f"{m}:{s:02d}"


def _fmt_date(ts: int) -> str:
    if not ts:
        return "未知"
    try:
        return datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d")
    except Exception:
        return "未知"


def _evidence_html(evidence: list[dict], max_show: int = 3) -> str:
    """Render evidence items as clickable links. Danmaku → ?t= timestamp; comment → video."""
    parts = []
    for ev in evidence[:max_show]:
        url = ev["url"]
        text = ev["text"]
        text_short = text[:22] + "…" if len(text) > 22 else text
        t = ev.get("t")
        ts_str = _fmt_time(t)
        if ts_str is not None:
            label = f"「{text_short}」▸ {ts_str}"
            title = f"弹幕 · {ev.get('video_title','')[:20]}"
        else:
            label = f"「{text_short}」· 评论区"
            title = ev.get("video_title", "")[:20]
        parts.append(
            f'<a href="{url}" target="_blank" rel="noreferrer noopener" title="{title}" '
            f'style="display:inline-block;margin:2px 4px 2px 0;padding:2px 8px;'
            f'background:#f0f7ff;border:1px solid #b8d9f8;border-radius:12px;'
            f'font-size:11px;color:#1a73e8;text-decoration:none;white-space:nowrap">'
            f'{label}</a>'
        )
    return "".join(parts)


def _card(icon: str, title: str, subtitle: str, evidence: list[dict], badge: str = "") -> None:
    badge_html = (
        f'<span style="background:#e8f4fd;color:#1a73e8;padding:2px 8px;'
        f'border-radius:10px;font-size:11px;margin-left:6px">{badge}</span>'
        if badge else ""
    )
    ev_html = _evidence_html(evidence) if evidence else ""
    ev_section = (
        f'<div style="margin-top:8px;line-height:1.8">{ev_html}</div>'
        if ev_html else ""
    )
    st.markdown(
        f'<div style="border:1px solid #e0e0e0;border-radius:10px;padding:14px 16px;'
        f'margin-bottom:10px;background:#fafafa">'
        f'<div style="font-size:15px;font-weight:600">{icon} {title}{badge_html}</div>'
        f'<div style="font-size:12px;color:#666;margin-top:3px">{subtitle}</div>'
        f'{ev_section}'
        f'</div>',
        unsafe_allow_html=True,
    )


def _section(title: str, items: list[dict], icon: str, key_field: str,
             subtitle_fn=None) -> None:
    st.markdown(f"### {title}")
    if not items:
        st.info("暂无数据")
        return
    cols = st.columns(min(len(items), 3))
    for i, item in enumerate(items):
        label = item.get(key_field, "")
        badge = f"{item.get('mentions', 0)} 条引用"
        sub = subtitle_fn(item) if subtitle_fn else item.get("aspect", "")
        ev = item.get("evidence", [])
        with cols[i % 3]:
            _card(icon, label, sub, ev, badge)


def _cache_key(name: str) -> str:
    return f"voc_{_slug(name)}"


# ── Result resolver: session cache → disk → fresh crawl ──────────────────────

def get_result(name: str, *, force: bool) -> tuple:
    """Return (records, videos, voc, origin) with origin in {session, disk, fresh}."""
    key = _cache_key(name)

    if not force:
        if key in st.session_state:
            return (*st.session_state[key], "session")
        saved = load_search(name)
        if saved:
            res = (saved["records"], saved["videos"], saved["voc"])
            st.session_state[key] = res
            return (*res, "disk")

    records = videos = voc = None

    with st.status(f"📡 正在抓取《{name}》B 站数据…", expanded=True) as status:
        # ── Step 1: crawl ─────────────────────────────────────────────
        try:
            records, videos = collect_corpus(
                name,
                sessdata=st.session_state.get("bili_sessdata"),
                log_fn=st.write,
            )
        except Exception as e:
            status.update(label="爬取失败", state="error")
            st.error(f"爬取失败：{e}")
            st.stop()

        if not records:
            status.update(label="未找到有效数据", state="error")
            st.warning("未抓取到相关弹幕/评论，请检查球拍名称或网络。如持续失败可通过登录B站进行配置 BILI_SESSDATA。")
            st.stop()

        total_d = sum(v["danmaku_count"] for v in videos)
        total_c = sum(v["comment_count"] for v in videos)
        st.write(
            f"📊 {len(videos)} 个视频 · 弹幕 {total_d} 条 · "
            f"评论 {total_c} 条 · 去重语料 {len(records)} 条"
        )
        status.update(label="✅ 抓取完成，开始 AI 分析…", state="running")

        # ── Step 2: LLM opinion mining ────────────────────────────────
        try:
            voc = analyze(records, videos, name, log_fn=st.write)
        except EnvironmentError as e:
            status.update(label="LLM 配置错误", state="error")
            st.error(str(e))
            st.stop()
        except Exception as e:
            status.update(label="LLM 分析失败", state="error")
            st.error(f"LLM 错误：{e}")
            st.stop()

        status.update(label="✅ 分析完成", state="complete", expanded=False)

    st.session_state[key] = (records, videos, voc)
    save_search(name, records, videos, voc,
                logged_in=bool(st.session_state.get("bili_sessdata")))
    return records, videos, voc, "fresh"


# ── Main ──────────────────────────────────────────────────────────────────────

# Resolve pending action (sidebar history click or rerun button)
pending = st.session_state.pop("pending", None)
if run_btn and racket_name.strip():
    pending = {"name": racket_name.strip(), "force": False}

if pending:
    name = pending["name"]
    records, videos, voc, origin = get_result(name, force=pending["force"])

    if origin == "disk":
        st.info("📂 已加载历史结果（无需重新爬取）。如需更新数据，点击下方按钮。")

    if st.button("🔄 重新分析并更新", type="secondary"):
        st.session_state["pending"] = {"name": name, "force": True}
        st.rerun()

    # ── Summary banner ────────────────────────────────────────────────────────
    if voc.get("summary"):
        st.markdown(
            f'<div style="background:#f0f7ff;border-left:4px solid #1a73e8;'
            f'padding:12px 16px;border-radius:6px;font-size:16px;margin-bottom:20px">'
            f'📋 <b>总体画像</b>：{voc["summary"]}</div>',
            unsafe_allow_html=True,
        )

    # ── 用户真实诉求 (headline) ───────────────────────────────────────────────
    st.markdown("---")
    _section(
        "🎯 用户真实诉求",
        voc.get("customer_needs", []),
        "🎯",
        key_field="need",
        subtitle_fn=lambda x: f'{x.get("aspect","")} · 情感：{x.get("sentiment","")}',
    )

    # ── Pain Points / Improvements / Drivers ─────────────────────────────────
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("#### 😤 痛点")
        for item in voc.get("pain_points", []):
            _card("😤", item.get("point", ""), item.get("aspect", ""),
                  item.get("evidence", []), f'{item.get("mentions",0)} 条')
        if not voc.get("pain_points"):
            st.info("无明显痛点")
    with col2:
        st.markdown("#### 💡 期望改进")
        for item in voc.get("desired_improvements", []):
            _card("💡", item.get("improvement", ""), "",
                  item.get("evidence", []), f'{item.get("mentions",0)} 条')
        if not voc.get("desired_improvements"):
            st.info("无改进建议")
    with col3:
        st.markdown("#### 🛒 购买驱动")
        for item in voc.get("purchase_drivers", []):
            _card("🛒", item.get("driver", ""), "",
                  item.get("evidence", []), f'{item.get("mentions",0)} 条')
        if not voc.get("purchase_drivers"):
            st.info("无明显驱动因素")

    # ── Positives / Negatives (collapsible) ──────────────────────────────────
    st.markdown("---")
    with st.expander("📊 正向 / 负向 速览（支撑证据）"):
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**🟢 正向亮点**")
            for item in voc.get("positives", []):
                _card("🟢", item.get("point", ""), item.get("aspect", ""),
                      item.get("evidence", []), f'{item.get("mentions",0)} 条')
        with c2:
            st.markdown("**🔴 负向问题**")
            for item in voc.get("negatives", []):
                _card("🔴", item.get("point", ""), item.get("aspect", ""),
                      item.get("evidence", []), f'{item.get("mentions",0)} 条')

    # ── Competitor comparison ─────────────────────────────────────────────────
    if voc.get("competitors"):
        st.markdown("---")
        st.markdown("### 🆚 竞品对照")
        for comp in voc["competitors"]:
            comp_name = comp.get("racket", "未知")
            with st.expander(f"**{comp_name}** — {comp.get('summary', '')}"):
                cc1, cc2 = st.columns(2)
                with cc1:
                    st.markdown("**🟢 正向**")
                    for item in comp.get("positives", []):
                        _card("🟢", item.get("point", ""), "",
                              item.get("evidence", []), f'{item.get("mentions",0)} 条')
                with cc2:
                    st.markdown("**🔴 负向**")
                    for item in comp.get("negatives", []):
                        _card("🔴", item.get("point", ""), "",
                              item.get("evidence", []), f'{item.get("mentions",0)} 条')

    # ── Reference videos (ranked) ─────────────────────────────────────────────
    st.markdown("---")
    with st.expander(f"📹 参考视频（共 {len(videos)} 个，按综合得分排序）"):
        for v in videos:
            pub = _fmt_date(v.get("pubdate", 0))
            play = v.get("play", 0)
            play_str = f"{play/10000:.1f}万" if play >= 10000 else str(play)
            dedicated_tag = " 🎯专评" if v.get("dedicated") else ""
            st.markdown(
                f"**{v['idx']+1}.** "
                f"[{v['title']}](https://www.bilibili.com/video/{v['bvid']}){dedicated_tag}  \n"
                f"UP：{v.get('author','未知')} · 发布：{pub} · "
                f"播放：{play_str} · 弹幕 {v['danmaku_count']} · 评论 {v['comment_count']} · "
                f"综合分 {v.get('score',0):.2f}"
            )

elif run_btn:
    st.warning("请输入球拍名称")
else:
    st.markdown(
        '<div style="text-align:center;padding:60px 0;color:#aaa">'
        '<div style="font-size:48px">🏸</div>'
        '<div style="font-size:18px;margin-top:12px">在左侧输入球拍名称，点击「开始分析」</div>'
        '<div style="font-size:13px;margin-top:8px">'
        "自动抓取 B 站评测弹幕与评论，AI挖掘用户真实诉求，每条结论可溯源至原始视频"
        "</div></div>",
        unsafe_allow_html=True,
    )
