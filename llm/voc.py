"""
Grounded opinion mining via map-reduce.

Map:    per-video chunks of records (with stable IDs) → opinion units that cite those IDs
Reduce: opinion units → structured VOC with evidence_ids selected by the LLM
Code:   validates IDs exist in records dict, resolves real text+URL, drops zero-evidence items
        → no fabricated quotes, truthful mention counts, traceable clickable links
"""
import json
import logging
from typing import Callable

from crawlers.bilibili import evidence_url
from llm.deepseek import chat, safe_json

logger = logging.getLogger(__name__)

_CHUNK_SIZE = 80   # records per map chunk
_REDUCE_CAP = 400  # max main units sent to reduce
_COMP_CAP = 50     # max units per competitor racket sent to reduce
_TOP_COMPS = 3     # max competitor rackets in reduce


def _log(msg: str, log_fn: Callable | None) -> None:
    """Milestone — goes to terminal AND UI."""
    logger.info(msg)
    if log_fn:
        log_fn(msg)


def _detail(msg: str) -> None:
    """Detail — terminal only."""
    logger.info(msg)


# ── Prompts ───────────────────────────────────────────────────────────────────

def _map_system(racket_name: str, video_title: str, dedicated: bool) -> str:
    ctx = f"正在分析视频《{video_title}》"
    if dedicated:
        ctx += f"（该视频专门评测「{racket_name}」）"
    return (
        "你是专业的消费者洞察分析师，从羽毛球拍弹幕/评论中挖掘用户真实意见。\n\n"
        + ctx + "\n"
        "目标球拍：" + racket_name + "\n\n"
        "输入格式：每行 [record_id] 评论文本\n\n"
        "对有实质内容的每条评论，输出 JSON 数组，每个元素包含：\n"
        '- id: 原始 record_id（必须与输入完全一致，例如 "v0d5"）\n'
        "- aspect: 涉及维度（打感/进攻/防守/品控/手感/挥速/性价比/适用人群/外观/重量/其他）\n"
        "- sentiment: 正/负/中\n"
        "- opinion: 核心观点（15字以内）\n"
        "- need: 背后真实诉求（20字以内）\n"
        "- type: 痛点|期望改进|购买驱动|使用场景|对比竞品|其他\n"
        "- target: 被评价的球拍。规则：\n"
        "    * 明确提到其他球拍名 → 该球拍名\n"
        "    * 明确指" + racket_name + "，或在专评视频中无歧义地指该拍 → \"" + racket_name + "\"\n"
        "    * 无法确定 → \"unclear\"\n\n"
        "忽略：纯表情/灌水/无关内容。每条评论只提取1个最主要意见单元。\n"
        "直接返回 JSON 数组，不要其他文字。"
    )


def _reduce_system(racket_name: str) -> str:
    return (
        "你是专业的产品洞察分析师。整合以下「" + racket_name + "」用户意见单元，生成 VOC 洞察报告。\n\n"
        "输入：JSON 对象，包含 units（主球拍意见单元，每个含 id 如 \"v0d5\"）和 competitors（竞品单元字典）。\n\n"
        "输出 JSON，格式如下（所有 evidence_ids 必须且只能来自输入中存在的 id，禁止编造）：\n"
        "{\n"
        '  "summary": "一句话总体画像（30字以内）",\n'
        '  "customer_needs": [{"need":"用户核心诉求","aspect":"维度","sentiment":"正/负/混合","evidence_ids":["v0d5","v1c3"]}],\n'
        '  "pain_points": [{"point":"...","aspect":"...","evidence_ids":[...]}],\n'
        '  "desired_improvements": [{"improvement":"...","evidence_ids":[...]}],\n'
        '  "purchase_drivers": [{"driver":"...","evidence_ids":[...]}],\n'
        '  "positives": [{"point":"...","aspect":"...","evidence_ids":[...]}],\n'
        '  "negatives": [{"point":"...","aspect":"...","evidence_ids":[...]}],\n'
        '  "competitors": [{"racket":"竞品名","summary":"一句对比","positives":[{"point":"...","evidence_ids":[...]}],"negatives":[{"point":"...","evidence_ids":[...]}]}]\n'
        "}\n\n"
        "要求：\n"
        "- 每个列表最多6条，按 evidence_ids 数量降序\n"
        "- evidence_ids 只能包含输入中存在的 id，禁止编造不存在的 id\n"
        "- customer_needs 是核心：从多条评论归纳用户真正想要什么（不是表面观点）\n"
        "- 无竞品数据时 competitors 返回空列表\n"
        "- 直接返回 JSON"
    )


# ── Map ───────────────────────────────────────────────────────────────────────

def _map_chunk(
    chunk: list[dict], racket_name: str, video: dict,
) -> list[dict]:
    lines = "\n".join(f"[{r['id']}] {r['text']}" for r in chunk)
    messages = [
        {"role": "system", "content": _map_system(
            racket_name, video["title"], video.get("dedicated", False)
        )},
        {"role": "user", "content": lines},
    ]
    raw = chat(messages, json_mode=True)
    result = safe_json(raw)
    if isinstance(result, list):
        extracted = result
    elif isinstance(result, dict):
        extracted = next((v for v in result.values() if isinstance(v, list)), [])
    else:
        extracted = []
    _detail(f"    → 提取 {len(extracted)} 个意见单元")
    return extracted


# ── Reduce ────────────────────────────────────────────────────────────────────

def _reduce(
    main_units: list[dict],
    competitor_units: dict[str, list[dict]],
    racket_name: str,
    log_fn: Callable | None,
) -> dict:
    payload = json.dumps(
        {"units": main_units, "competitors": competitor_units},
        ensure_ascii=False, separators=(",", ":"),
    )
    messages = [
        {"role": "system", "content": _reduce_system(racket_name)},
        {"role": "user", "content": payload},
    ]
    _log("🧠 Reduce：汇总归类，生成 VOC 洞察报告…", log_fn)
    raw = chat(messages, json_mode=True)
    result = safe_json(raw)
    return result if isinstance(result, dict) else {}


# ── Grounding / evidence resolution ──────────────────────────────────────────

def _resolve_evidence(ids: list, records_by_id: dict) -> list[dict]:
    """Validate IDs against records and resolve to real text + deep links."""
    evidence = []
    for eid in (ids or []):
        rec = records_by_id.get(str(eid))
        if rec is None:
            continue  # LLM invented this ID — drop silently
        evidence.append({
            "text": rec["text"],
            "url": evidence_url(rec),
            "source": rec["source"],
            "video_title": rec["video_title"],
            "t": rec.get("t"),
        })
    return evidence


def _resolve_section(items: list[dict], records_by_id: dict) -> list[dict]:
    """Resolve evidence for section items; drop items with zero valid evidence."""
    resolved = []
    for item in (items or []):
        ev = _resolve_evidence(item.get("evidence_ids", []), records_by_id)
        if not ev:
            continue
        out = {k: v for k, v in item.items() if k != "evidence_ids"}
        out["evidence"] = ev
        out["mentions"] = len(ev)
        resolved.append(out)
    return sorted(resolved, key=lambda x: x["mentions"], reverse=True)[:6]


# ── Main entry ────────────────────────────────────────────────────────────────

def _empty_result() -> dict:
    return {
        "summary": "",
        "customer_needs": [],
        "pain_points": [],
        "desired_improvements": [],
        "purchase_drivers": [],
        "positives": [],
        "negatives": [],
        "competitors": [],
    }


def analyze(
    records: list[dict],
    videos: list[dict],
    racket_name: str,
    log_fn: Callable | None = None,
) -> dict:
    """
    Grounded opinion mining pipeline.

    records: output of collect_corpus() — list of record dicts with stable 'id'.
    videos:  ranked video list with 'dedicated' flag and 'idx'.
    racket_name: queried racket (used for per-racket attribution and competitor split).

    Returns structured VOC dict where every displayed quote is resolved from a real record
    (no LLM-fabricated text) and includes a clickable URL (danmaku → ?t=, comment → video).
    """
    if not records:
        _log("⚠️ 语料为空，跳过分析", log_fn)
        return _empty_result()

    records_by_id: dict[str, dict] = {r["id"]: r for r in records}
    videos_by_idx: dict[int, dict] = {v["idx"]: v for v in videos}
    norm_name = racket_name.strip()

    # ── Map phase: per video ──────────────────────────────────────────────────
    all_units: list[dict] = []
    _log(f"🤖 Map 阶段：{len(videos)} 个视频", log_fn)

    for video in videos:
        v_idx = video["idx"]
        v_records = [r for r in records if r["video_idx"] == v_idx]
        if not v_records:
            continue
        short_title = video["title"][:30] + ("…" if len(video["title"]) > 30 else "")
        chunks = [v_records[i:i + _CHUNK_SIZE] for i in range(0, len(v_records), _CHUNK_SIZE)]
        _log(f"  🤖 分析《{short_title}》（{len(v_records)} 条，{len(chunks)} 批）", log_fn)

        for ci, chunk in enumerate(chunks, 1):
            _detail(f"    第 {ci}/{len(chunks)} 批（{len(chunk)} 条）…")
            units = _map_chunk(chunk, norm_name, video)
            all_units.extend(units)

    _log(f"✅ 意见单元提取完成：共 {len(all_units)} 条", log_fn)

    # ── Ground: validate IDs ──────────────────────────────────────────────────
    valid_units = [u for u in all_units if u.get("id") in records_by_id]
    dropped = len(all_units) - len(valid_units)
    if dropped:
        _detail(f"  ✂️ 丢弃 {dropped} 个 ID 无效的单元（LLM 幻觉）")

    # ── Partition: main racket vs competitors ─────────────────────────────────
    main_units: list[dict] = []
    competitor_buckets: dict[str, list[dict]] = {}

    for u in valid_units:
        target = (u.get("target") or "").strip()
        if target == norm_name:
            main_units.append(u)
        elif target == "unclear":
            rec = records_by_id.get(u.get("id", ""))
            if rec and videos_by_idx.get(rec["video_idx"], {}).get("dedicated"):
                main_units.append(u)
        elif target and target not in ("unclear", norm_name):
            competitor_buckets.setdefault(target, []).append(u)

    n_comp_units = sum(len(v) for v in competitor_buckets.values())
    _detail(f"  主球拍 {len(main_units)} 条，竞品 {n_comp_units} 条（{len(competitor_buckets)} 款）")

    if not main_units:
        _log("⚠️ 无有效主球拍意见单元", log_fn)
        return _empty_result()

    # ── Reduce ────────────────────────────────────────────────────────────────
    capped_main = main_units[:_REDUCE_CAP]
    if len(main_units) > _REDUCE_CAP:
        _detail(f"  ✂️ 主单元截取前 {_REDUCE_CAP} 条进入 Reduce")

    # Top competitor rackets by unit count
    top_comps = sorted(competitor_buckets.items(), key=lambda x: len(x[1]), reverse=True)[:_TOP_COMPS]
    capped_comps = {k: v[:_COMP_CAP] for k, v in top_comps}

    _log("🔀 开始 Reduce 阶段…", log_fn)
    raw_result = _reduce(capped_main, capped_comps, norm_name, log_fn)

    if not raw_result:
        _log("⚠️ Reduce 返回空结果", log_fn)
        return _empty_result()

    # ── Resolve evidence (validate IDs → real text + clickable URLs) ──────────
    result: dict = {"summary": raw_result.get("summary", ""), "competitors": []}

    for section_key in ("customer_needs", "pain_points", "desired_improvements",
                         "purchase_drivers", "positives", "negatives"):
        result[section_key] = _resolve_section(
            raw_result.get(section_key, []), records_by_id
        )

    for comp in (raw_result.get("competitors") or []):
        resolved_comp = {
            "racket": comp.get("racket", ""),
            "summary": comp.get("summary", ""),
            "positives": _resolve_section(comp.get("positives", []), records_by_id),
            "negatives": _resolve_section(comp.get("negatives", []), records_by_id),
        }
        if resolved_comp["positives"] or resolved_comp["negatives"]:
            result["competitors"].append(resolved_comp)

    _log("✅ 分析完成", log_fn)
    return result
