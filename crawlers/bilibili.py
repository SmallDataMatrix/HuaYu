import logging
import math
import re
import time
from typing import Callable

from bs4 import BeautifulSoup

from config import (
    BILI_MAX_VIDEOS, BILI_MAX_COMMENTS, MAX_CORPUS,
    BILI_SEARCH_CANDIDATES, RELEVANCE_MENTION_THRESHOLD,
    SCORE_W_PLAY, SCORE_W_RECENCY, RECENCY_HALFLIFE_DAYS,
    ANON_MAX_VIDEOS, ANON_MAX_COMMENTS, ANON_MIN_DELAY, ANON_MAX_DELAY,
)
from crawlers.wbi import make_session, get_nav_info, sign_params, polite_get

logger = logging.getLogger(__name__)


def _log(msg: str, log_fn: Callable | None) -> None:
    """Milestone log — goes to terminal AND to the UI status box."""
    logger.info(msg)
    if log_fn:
        log_fn(msg)


def _detail(msg: str) -> None:
    """Detail log — terminal only; keeps the UI status box clean."""
    logger.info(msg)


def _normalize(text: str) -> str:
    """Lowercase + strip spaces/punctuation for fuzzy racket-name matching."""
    return re.sub(r"[\s\-_·•·【】《》「」『』]", "", text).lower()


def evidence_url(rec: dict) -> str:
    """Deep link to the source video; danmaku with offset → ?t=N."""
    base = f"https://www.bilibili.com/video/{rec['bvid']}"
    t = rec.get("t")
    if t is not None:
        return f"{base}?t={int(t)}"
    return base


def _clean_comment(text: str) -> str:
    text = re.sub(r"\{.*?\}", "", text)
    text = re.sub(r"@\S+", "", text)
    return text.strip()


def _blended_score(v: dict) -> float:
    age_days = max(0.0, (time.time() - (v.get("pubdate") or 0)) / 86400)
    recency = 0.5 ** (age_days / RECENCY_HALFLIFE_DAYS)
    play_score = math.log10(max(1, v.get("play", 0)) + 1)
    return SCORE_W_PLAY * play_score + SCORE_W_RECENCY * recency


def _search_queries(racket_name: str) -> list[str]:
    """
    Generate multiple search queries for a racket name.
    Reviewers rarely use the full model name — they shorten it or omit the brand.
    Strategy: bare name first, then common review keywords, then a short-name fallback.
    """
    name = racket_name.strip()
    queries = [
        name,                        # "华羽屠夫"  (most specific — best relevance signal)
        f"{name} 测评",               # "华羽屠夫 测评"
        f"{name} 评测",               # "华羽屠夫 评测"
        f"{name} 上手",               # "华羽屠夫 上手"
        f"羽毛球拍 {name}",            # reversed (some titles put brand last)
    ]
    # Short-name fallback: last 2 chars often carry the model identity ("屠夫", "AX99")
    # Only add if the name is long enough that truncation is meaningful
    short = re.sub(r"[\s\-_]", "", name)
    if len(short) >= 4:
        suffix = short[-2:]          # e.g. "屠夫" from "华羽屠夫"
        if suffix and suffix != name:
            queries.append(f"{suffix} 羽毛球拍 测评")
    return queries


def search_candidates(
    session, keyword: str, img_key: str, sub_key: str,
    n: int, log_fn: Callable | None = None,
    delay_range: tuple | None = None,
) -> list[dict]:
    """
    Fetch up to n video candidates with full metadata.

    Uses the non-WBI search endpoint which works for both anonymous and logged-in
    sessions. The WBI search endpoint silently returns empty results for anonymous
    users (Bilibili requires login for WBI search as of 2024).
    """
    # Non-WBI endpoint works anonymously; WBI search requires login (returns v_voucher only)
    url_plain = "https://api.bilibili.com/x/web-interface/search/type"
    url_wbi   = "https://api.bilibili.com/x/web-interface/wbi/search/type"

    videos: list[dict] = []
    page = 1
    _detail(f"🔎 搜索：「{keyword}」（每轮最多 {n} 个）")

    while len(videos) < n:
        base_params = {"search_type": "video", "keyword": keyword,
                       "page": page, "order": "totalrank"}

        # Try plain endpoint first; if it returns no data fall back to WBI
        resp = polite_get(session, url_plain, delay_range=delay_range,
                          params=base_params, timeout=10)
        if resp is None:
            _detail("  ⚠️ 搜索请求失败")
            break
        try:
            data = resp.json()
        except Exception:
            break

        # Plain endpoint gave empty/error → retry with WBI-signed params
        result_raw = (data.get("data") or {}).get("result")
        if data.get("code") != 0 or not result_raw:
            _detail("  ↩️ 普通搜索无结果，尝试 WBI 签名搜索…")
            signed = sign_params(base_params, img_key, sub_key)
            resp2 = polite_get(session, url_wbi, delay_range=delay_range,
                               params=signed, timeout=10)
            if resp2 is None:
                break
            try:
                data = resp2.json()
            except Exception:
                break
            result_raw = (data.get("data") or {}).get("result")

        if data.get("code") != 0:
            _detail(f"  ⚠️ B站错误 code={data.get('code')} msg={data.get('message','')}")
            break

        results = result_raw if isinstance(result_raw, list) else []
        if not results:
            break

        for v in results:
            if v.get("type") != "video":
                continue
            title = re.sub(r"</?em[^>]*>", "", v.get("title", ""))
            desc  = re.sub(r"<[^>]+>", "", v.get("description", ""))
            videos.append({
                "aid":         v["aid"],
                "bvid":        v["bvid"],
                "title":       title,
                "cid":         v.get("cid", 0),
                "author":      v.get("author", ""),
                "mid":         v.get("mid", 0),
                "play":        v.get("play", 0) or v.get("view", 0),
                "pubdate":     v.get("pubdate", 0),
                "duration":    v.get("duration", ""),
                "description": desc,
                "tag":         v.get("tag", ""),
            })
            if len(videos) >= n:
                break
        page += 1

    _detail(f"  → 本轮获取 {len(videos)} 个")
    return videos


def get_cid(session, bvid: str, log_fn: Callable | None = None,
            delay_range: tuple | None = None) -> int:
    url = f"https://api.bilibili.com/x/player/pagelist?bvid={bvid}"
    resp = polite_get(session, url, log_fn=log_fn, delay_range=delay_range, timeout=10)
    if resp is None:
        return 0
    try:
        data = resp.json()
        if data["code"] == 0 and data["data"]:
            return data["data"][0]["cid"]
    except Exception as e:
        _detail(f"  ⚠️ 获取 cid 失败 ({bvid}): {e}")
    return 0


def get_danmaku(
    session, cid: int, log_fn: Callable | None = None,
    delay_range: tuple | None = None,
) -> list[tuple[str, float | None]]:
    """
    Fetch danmaku XML and return [(text, offset_seconds)].
    offset_seconds is float (in-video time) from the 'p' attribute; None on parse failure.
    """
    url = f"https://comment.bilibili.com/{cid}.xml"
    resp = polite_get(session, url, log_fn=log_fn, delay_range=delay_range, timeout=15)
    if resp is None:
        _detail("    ⚠️ 弹幕请求失败")
        return []
    try:
        resp.encoding = "utf-8"
        soup = BeautifulSoup(resp.text, "lxml-xml")
        items: list[tuple[str, float | None]] = []
        for d in soup.find_all("d"):
            text = d.text
            if not text:
                continue
            p_attr = d.get("p", "")
            try:
                t: float | None = float(p_attr.split(",")[0])
            except (ValueError, IndexError):
                t = None
            items.append((text, t))
        _detail(f"    弹幕 {len(items)} 条")
        return items
    except Exception as e:
        _detail(f"    ⚠️ 弹幕解析失败: {e}")
        return []


def get_comments(
    session, aid: int, img_key: str, sub_key: str,
    max_count: int, log_fn: Callable | None = None,
    delay_range: tuple | None = None,
) -> list[str]:
    url = "https://api.bilibili.com/x/v2/reply/wbi/main"
    comments: list[str] = []
    cursor = 0
    for page_num in range(1, 6):
        params = sign_params(
            {"type": 1, "oid": aid, "mode": 3, "next": cursor},
            img_key, sub_key,
        )
        resp = polite_get(session, url, log_fn=log_fn, delay_range=delay_range, params=params, timeout=10)
        if resp is None:
            _detail(f"    ⚠️ 评论请求失败 page {page_num}")
            break
        try:
            data = resp.json()
        except Exception:
            break
        if data.get("code") != 0:
            _detail(f"    ⚠️ 评论接口错误 code={data.get('code')}")
            break
        replies = (data.get("data") or {}).get("replies") or []
        before = len(comments)
        for r in replies:
            text = _clean_comment(r["content"]["message"])
            if len(text) >= 4:
                comments.append(text)
        _detail(f"    评论第 {page_num} 页 +{len(comments)-before} 条")
        cursor_info = (data.get("data") or {}).get("cursor") or {}
        cursor = cursor_info.get("next", 0)
        if cursor_info.get("is_end") or not cursor:
            break
        if len(comments) >= max_count:
            break
    return comments[:max_count]


def collect_corpus(
    racket_name: str,
    sessdata: str | None = None,
    log_fn: Callable | None = None,
) -> tuple[list[dict], list[dict]]:
    """
    Search Bilibili, apply relevance filter + blended ranking, collect records.

    Returns:
        records: list of {id, text, source, bvid, video_idx, video_title, t}
                 id format: "v{video_idx}d{n}" for danmaku, "v{video_idx}c{n}" for comments.
                 t: float offset in seconds for danmaku, None for comments.
        videos:  ranked list of {idx, bvid, aid, title, author, mid, play, pubdate,
                                  duration, score, danmaku_count, comment_count, dedicated}
    """
    _log("⚙️  初始化 B 站会话，获取 WBI 签名密钥…", log_fn)
    session = make_session(sessdata=sessdata)
    nav = get_nav_info(session)
    img_key, sub_key = nav["img_key"], nav["sub_key"]

    # ── Mode selection: logged-in vs anonymous ───────────────────────────────
    logged_in = nav["is_login"]
    if logged_in:
        _log(f"  ✅ WBI 密钥获取成功 · 已登录账号：{nav['uname']}", log_fn)
        effective_max_videos   = BILI_MAX_VIDEOS
        effective_max_comments = BILI_MAX_COMMENTS
        delay_range            = None   # use config defaults
    else:
        _log(
            f"  ⚠️ 匿名模式：限制为 {ANON_MAX_VIDEOS} 个视频 / "
            f"{ANON_MAX_COMMENTS} 条评论，间隔 {ANON_MIN_DELAY}–{ANON_MAX_DELAY}s。"
            "登录后可获取更多数据。",
            log_fn,
        )
        effective_max_videos   = ANON_MAX_VIDEOS
        effective_max_comments = ANON_MAX_COMMENTS
        delay_range            = (ANON_MIN_DELAY, ANON_MAX_DELAY)

    # ── Multi-query search (reviewers use short names / different keywords) ────
    queries = _search_queries(racket_name)
    seen_bvids: set[str] = set()
    candidates: list[dict] = []
    per_query = max(5, BILI_SEARCH_CANDIDATES // len(queries))

    for q in queries:
        if len(candidates) >= BILI_SEARCH_CANDIDATES:
            break
        batch = search_candidates(session, q, img_key, sub_key,
                                   per_query, log_fn, delay_range)
        added = 0
        for v in batch:
            if v["bvid"] not in seen_bvids:
                seen_bvids.add(v["bvid"])
                candidates.append(v)
                added += 1
        _detail(f"  查询「{q}」→ {len(batch)} 个，新增 {added} 个")
    _log(f"🔍 搜索完成：{len(candidates)} 个候选视频（{len(queries)} 轮查询去重）", log_fn)
    if not candidates:
        _log("❌ 未找到候选视频，请尝试更短的球拍名称或检查网络", log_fn)
        return [], []

    norm_name = _normalize(racket_name)

    # ── Relevance pre-filter (metadata level) ────────────────────────────────
    meta_hits: list[dict] = []
    tentative: list[dict] = []
    for v in candidates:
        haystack = _normalize(
            v["title"] + " " + v.get("description", "") + " " + v.get("tag", "")
        )
        v["dedicated"] = norm_name in _normalize(v["title"])
        if norm_name in haystack:
            meta_hits.append(v)
        else:
            tentative.append(v)

    _detail(f"  元数据命中 {len(meta_hits)} 个，待内容验证 {len(tentative)} 个")

    # Rank all candidates by blended score; process top ones first
    all_ranked = sorted(meta_hits + tentative, key=_blended_score, reverse=True)

    # ── Fetch content + build records ────────────────────────────────────────
    records: list[dict] = []
    kept_videos: list[dict] = []
    seen_texts: set[str] = set()

    for v in all_ranked:
        if len(kept_videos) >= effective_max_videos:
            break
        if len(records) >= MAX_CORPUS:
            break

        video_idx = len(kept_videos)
        short_title = v["title"][:32] + ("…" if len(v["title"]) > 32 else "")

        cid = v["cid"] or get_cid(session, v["bvid"], delay_range=delay_range)
        danmaku_pairs = get_danmaku(session, cid, delay_range=delay_range) if cid else []
        raw_comments  = get_comments(session, v["aid"], img_key, sub_key,
                                      effective_max_comments, delay_range=delay_range)

        # Build danmaku records with stable IDs and timestamps
        d_recs: list[dict] = []
        for n, (text, t) in enumerate(danmaku_pairs):
            if len(text) < 4 or text.startswith("http"):
                continue
            if text in seen_texts:
                continue
            seen_texts.add(text)
            d_recs.append({
                "id": f"v{video_idx}d{n}",
                "text": text,
                "source": "danmaku",
                "bvid": v["bvid"],
                "video_idx": video_idx,
                "video_title": v["title"],
                "t": t,
            })

        # Build comment records
        c_recs: list[dict] = []
        for n, text in enumerate(raw_comments):
            if len(text) < 4:
                continue
            if text in seen_texts:
                continue
            seen_texts.add(text)
            c_recs.append({
                "id": f"v{video_idx}c{n}",
                "text": text,
                "source": "comment",
                "bvid": v["bvid"],
                "video_idx": video_idx,
                "video_title": v["title"],
                "t": None,
            })

        all_recs = d_recs + c_recs
        mention_count = sum(1 for r in all_recs if norm_name in _normalize(r["text"]))

        # Post-fetch relevance gate for non-meta-hit videos
        is_meta_hit = v in meta_hits
        if not is_meta_hit and mention_count < RELEVANCE_MENTION_THRESHOLD:
            _detail(f"    ⏭️ 跳过（仅提及 {mention_count} 次，阈值 {RELEVANCE_MENTION_THRESHOLD}）")
            continue

        budget = MAX_CORPUS - len(records)
        records.extend(all_recs[:budget])

        play_str = f"{v['play']/10000:.1f}万" if v.get("play", 0) >= 10000 else str(v.get("play", 0))
        _log(
            f"📹 [{video_idx+1}/{effective_max_videos}] 《{short_title}》"
            f"  弹幕 {len([x for x in danmaku_pairs if x[0]])} · 评论 {len(raw_comments)} · 播放 {play_str}",
            log_fn,
        )

        kept_videos.append({
            "idx": video_idx,
            "bvid": v["bvid"],
            "aid": v["aid"],
            "title": v["title"],
            "author": v["author"],
            "mid": v.get("mid", 0),
            "play": v.get("play", 0),
            "pubdate": v.get("pubdate", 0),
            "duration": v.get("duration", ""),
            "score": _blended_score(v),
            "danmaku_count": len(d_recs),
            "comment_count": len(c_recs),
            "dedicated": v.get("dedicated", False),
        })

    _log(f"✅ 爬取完成：{len(kept_videos)} 个视频，{len(records)} 条语料", log_fn)
    return records, kept_videos
