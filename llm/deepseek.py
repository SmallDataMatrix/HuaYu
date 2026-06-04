"""
Thin DeepSeek chat client (OpenAI-compatible API).
Requires DEEPSEEK_API_KEY in environment or .env file.
"""
import json
import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

_client: OpenAI | None = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        api_key = os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            raise EnvironmentError(
                "DEEPSEEK_API_KEY not set. Add it to .env or your environment."
            )
        from app_config import DEEPSEEK_BASE_URL
        _client = OpenAI(api_key=api_key, base_url=DEEPSEEK_BASE_URL)
    return _client


def chat(messages: list[dict], json_mode: bool = False) -> str:
    """Call DeepSeek chat; return response content string."""
    from app_config import DEEPSEEK_MODEL
    kwargs: dict = {}
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    resp = _get_client().chat.completions.create(
        model=DEEPSEEK_MODEL,
        messages=messages,
        **kwargs,
    )
    return resp.choices[0].message.content or ""


def safe_json(text: str) -> dict | list:
    """Parse JSON from LLM output, stripping markdown fences."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1]
        text = text.rsplit("```", 1)[0]
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {}
