"""
Bilibili QR-code login flow (no password needed).
Each call creates a fresh requests.Session so cookies don't bleed between users.
"""
from __future__ import annotations

import logging
from io import BytesIO

import requests

logger = logging.getLogger(__name__)

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.bilibili.com/",
}
_GENERATE_URL = "https://passport.bilibili.com/x/passport-login/web/qrcode/generate"
_POLL_URL     = "https://passport.bilibili.com/x/passport-login/web/qrcode/poll"


# ── Poll status codes returned by Bilibili ────────────────────────────────────
_CODE_SUCCESS  = 0      # login confirmed
_CODE_SCANNED  = 86090  # scanned on phone, waiting for tap-confirm
_CODE_WAITING  = 86101  # not yet scanned
_CODE_EXPIRED  = 86038  # QR code timed out


def _make_login_session() -> requests.Session:
    """Lightweight session just for the login flow (gets buvid3 cookie)."""
    sess = requests.Session()
    sess.headers.update(_HEADERS)
    try:
        sess.get("https://www.bilibili.com", timeout=8)
    except Exception:
        pass
    return sess


def start_login() -> dict | None:
    """
    Bootstrap a login session and generate a fresh QR code.

    Returns:
        {"key": qrcode_key, "url": qrcode_url,
         "img_bytes": PNG bytes, "cookies": dict}
        or None on failure.
    """
    sess = _make_login_session()
    try:
        resp = sess.get(_GENERATE_URL, timeout=10)
        data = resp.json()
        if data.get("code") != 0:
            logger.warning(f"QR 生成失败 code={data.get('code')}")
            return None
        qr_url = data["data"]["url"]
        key    = data["data"]["qrcode_key"]
        return {
            "key":       key,
            "url":       qr_url,
            "img_bytes": _qr_image_bytes(qr_url),
            "cookies":   dict(sess.cookies),
        }
    except Exception as e:
        logger.warning(f"QR 生成异常: {e}")
        return None


def poll_login(key: str, cookies: dict) -> dict:
    """
    Poll scan status for the given QR key.
    Pass the cookies dict returned by start_login() so the server recognises the session.

    Returns:
        {"status": "success"|"scanned"|"waiting"|"expired"|"error",
         "sessdata": str | None}
    """
    sess = requests.Session()
    sess.headers.update(_HEADERS)
    sess.cookies.update(cookies)
    try:
        resp = sess.get(_POLL_URL, params={"qrcode_key": key}, timeout=10)
        outer = resp.json()
        if outer.get("code") != 0:
            return {"status": "error", "sessdata": None}

        inner_code = outer["data"]["code"]

        if inner_code == _CODE_SUCCESS:
            # SESSDATA is set via Set-Cookie on this response
            sessdata = resp.cookies.get("SESSDATA") or sess.cookies.get("SESSDATA")
            return {"status": "success", "sessdata": sessdata}
        if inner_code == _CODE_SCANNED:
            return {"status": "scanned", "sessdata": None}
        if inner_code == _CODE_WAITING:
            return {"status": "waiting", "sessdata": None}
        if inner_code == _CODE_EXPIRED:
            return {"status": "expired", "sessdata": None}
        return {"status": "error", "sessdata": None}

    except Exception as e:
        logger.warning(f"QR 轮询异常: {e}")
        return {"status": "error", "sessdata": None}


def verify_sessdata(sessdata: str) -> str:
    """
    Call /x/web-interface/nav with the given SESSDATA.
    Returns the Bilibili username, or "" if the cookie is invalid/expired.
    """
    from crawlers.wbi import make_session, get_nav_info
    try:
        sess = make_session(sessdata=sessdata)
        nav  = get_nav_info(sess)
        if nav.get("is_login"):
            return nav.get("uname", "")
    except Exception:
        pass
    return ""


def _qr_image_bytes(url: str) -> bytes:
    """Render the login URL as a PNG QR code and return the raw bytes."""
    import qrcode  # type: ignore[import]
    img = qrcode.make(url)
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
