"""
Bilibili WBI request signing + polite session management.
Reference: https://socialsisteryi.github.io/bilibili-API-collect/docs/misc/sign/wbi.html
"""
import hashlib
import logging
import os
import random
import time
import urllib.parse

import requests

from app_config import BILI_MIN_DELAY, BILI_MAX_DELAY, BILI_RETRIES, UA_POOL

logger = logging.getLogger(__name__)

_MIXIN_KEY_ENC_TAB = [
    46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35,
    27, 43, 5, 49, 33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13,
    37, 48, 7, 16, 24, 55, 40, 61, 26, 17, 0, 1, 60, 51, 30, 4,
    22, 25, 54, 21, 56, 59, 6, 63, 57, 62, 11, 36, 20, 34, 44, 52,
]

_last_request_time: float = 0.0


def _get_mixin_key(img_key: str, sub_key: str) -> str:
    raw = img_key + sub_key
    return "".join(raw[i] for i in _MIXIN_KEY_ENC_TAB)[:32]


def _extract_key(url: str) -> str:
    return urllib.parse.urlparse(url).path.rsplit("/", 1)[-1].split(".")[0]


def polite_get(
    session: requests.Session,
    url: str,
    log_fn=None,
    delay_range: "tuple[float, float] | None" = None,
    **kwargs,
) -> "requests.Response | None":
    """
    Throttled, retrying GET. Single choke point for all Bilibili requests.
    - Enforces random delay between BILI_MIN_DELAY and BILI_MAX_DELAY
      (or the caller-supplied delay_range for anonymous / conservative mode).
    - Retries BILI_RETRIES times with exponential backoff on network errors.
    - On HTTP 412/429/403 (risk control): logs a warning, backs off, retries.
    Returns None if all attempts fail.
    """
    global _last_request_time
    min_d, max_d = delay_range if delay_range else (BILI_MIN_DELAY, BILI_MAX_DELAY)
    elapsed = time.time() - _last_request_time
    gap = random.uniform(min_d, max_d)
    if elapsed < gap:
        time.sleep(gap - elapsed)

    for attempt in range(1, BILI_RETRIES + 1):
        try:
            resp = session.get(url, **kwargs)
            _last_request_time = time.time()

            if resp.status_code in (412, 429, 403):
                cooldown = min(5 * attempt, 30)
                msg = f"⚠️ 触发限流/风控 HTTP {resp.status_code}，冷却 {cooldown}s 后重试…"
                logger.warning(msg)
                if log_fn:
                    log_fn(msg)
                time.sleep(cooldown)
                _last_request_time = time.time()
                continue

            return resp

        except requests.RequestException as e:
            wait = 2 ** attempt + random.random()
            logger.warning(f"请求失败 attempt={attempt}/{BILI_RETRIES}: {e}，等待 {wait:.1f}s")
            if attempt < BILI_RETRIES:
                time.sleep(wait)

    return None


def auto_detect_sessdata() -> tuple[str, str] | None:
    """
    Try to read a valid SESSDATA cookie from installed browsers on this machine.
    Returns (sessdata_value, browser_name) or None if not found / not installed.
    Tries Chrome → Edge → Firefox in order.
    """
    try:
        import browser_cookie3
    except ImportError:
        return None

    browsers = [
        ("Chrome",  browser_cookie3.chrome),
        ("Edge",    browser_cookie3.edge),
        ("Firefox", browser_cookie3.firefox),
    ]
    for name, loader in browsers:
        try:
            jar = loader(domain_name=".bilibili.com")
            for cookie in jar:
                if cookie.name == "SESSDATA" and cookie.value:
                    return cookie.value, name
        except Exception:
            continue
    return None


def get_nav_info(session: requests.Session) -> dict:
    """
    Call /x/web-interface/nav once, return WBI keys + login status.
    {img_key, sub_key, is_login, uname, mid}
    """
    resp = polite_get(session, "https://api.bilibili.com/x/web-interface/nav", timeout=10)
    if resp is None:
        raise RuntimeError("无法连接到 B 站，请检查网络")
    payload = resp.json().get("data", {})
    wbi_img = payload.get("wbi_img", {})
    return {
        "img_key": _extract_key(wbi_img.get("img_url", "")),
        "sub_key": _extract_key(wbi_img.get("sub_url", "")),
        "is_login": payload.get("isLogin", False),
        "uname": payload.get("uname", ""),
        "mid": payload.get("mid", 0),
    }


def get_wbi_keys(session: requests.Session) -> tuple[str, str]:
    """Backward-compat wrapper around get_nav_info."""
    info = get_nav_info(session)
    return info["img_key"], info["sub_key"]


def sign_params(params: dict, img_key: str, sub_key: str) -> dict:
    mixin_key = _get_mixin_key(img_key, sub_key)
    params = dict(params)
    params["wts"] = int(time.time())
    query = urllib.parse.urlencode(sorted(params.items()))
    w_rid = hashlib.md5((query + mixin_key).encode()).hexdigest()
    params["w_rid"] = w_rid
    return params


def make_session(sessdata: str | None = None) -> requests.Session:
    """
    Create a hardened crawl session.

    sessdata: the user's SESSDATA cookie (obtained via QR login or .env fallback).
              When provided, the session runs as a logged-in user.
              When None, falls back to the BILI_SESSDATA env var (server default).
    """
    ua = random.choice(UA_POOL)
    session = requests.Session()
    session.headers.update({
        "User-Agent": ua,
        "Referer": "https://www.bilibili.com/",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Origin": "https://www.bilibili.com",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-site",
    })

    # Prime buvid3 via homepage visit
    try:
        session.get("https://www.bilibili.com", timeout=10)
    except Exception:
        pass

    # Fetch buvid3/buvid4 from fingerprint endpoint
    try:
        resp = session.get(
            "https://api.bilibili.com/x/frontend/finger/spi", timeout=10
        )
        d = resp.json().get("data", {})
        if d.get("b_3"):
            session.cookies.set("buvid3", d["b_3"], domain=".bilibili.com")
        if d.get("b_4"):
            session.cookies.set("buvid4", d["b_4"], domain=".bilibili.com")
    except Exception:
        pass

    # Caller-supplied SESSDATA takes priority; fall back to env var (server default)
    effective = (sessdata or "").strip() or os.getenv("BILI_SESSDATA", "").strip()
    if effective:
        session.cookies.set("SESSDATA", effective, domain=".bilibili.com")
        src = "用户登录" if sessdata else ".env"
        logger.info(f"✅ 已使用 B站登录 Cookie（{src}）")

    return session
