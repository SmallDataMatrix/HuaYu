import os
from pathlib import Path

# ── Default product ───────────────────────────────────────────────────────────
PRODUCT_NAME = "华羽屠夫"

# ── Data persistence directory ────────────────────────────────────────────────
DATA_DIR = os.getenv("DATA_DIR", str(Path(__file__).parent / "data"))

# ── Anti-crawl settings ───────────────────────────────────────────────────────
BILI_MIN_DELAY = 1.0        # min seconds between requests
BILI_MAX_DELAY = 2.5        # max seconds between requests
BILI_RETRIES = 3            # retries on network error / risk-control response

UA_POOL = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]

# ── Bilibili crawler settings — logged-in mode ───────────────────────────────
BILI_SEARCH_CANDIDATES = 20   # candidate pool before relevance filter
BILI_MAX_VIDEOS = 5           # kept after relevance + ranking
BILI_MAX_COMMENTS = 200       # max comments per video
MAX_CORPUS = 2000             # total record cap (bounds LLM token cost)
RELEVANCE_MENTION_THRESHOLD = 3  # minimum times racket name must appear

# ── Anonymous mode overrides (more conservative to reduce ban risk) ────────────
ANON_MAX_VIDEOS = 3           # fewer videos to limit request volume
ANON_MAX_COMMENTS = 50        # fewer comment pages per video
ANON_MIN_DELAY = 2.5          # longer minimum gap between requests
ANON_MAX_DELAY = 5.0          # longer maximum gap

# ── Video blended ranking weights ─────────────────────────────────────────────
SCORE_W_PLAY = 0.7            # weight for log10(play_count+1)
SCORE_W_RECENCY = 0.3         # weight for recency decay
RECENCY_HALFLIFE_DAYS = 180   # decay half-life (~6 months)

# ── DeepSeek LLM settings ─────────────────────────────────────────────────────
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_MODEL = "deepseek-chat"
