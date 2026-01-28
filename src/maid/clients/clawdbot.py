import os
from typing import Optional, List

from moltbot import chat_once_async

from maid.utils.logger import logger


def clawdbot_enabled() -> bool:
    """Check if Clawdbot relay mode is enabled via environment variable."""
    flag = os.getenv("CLAWDBOT_ENABLED", "").strip().lower()
    return flag in {"1", "true", "yes", "on", "enable"}


def _parse_scopes() -> Optional[List[str]]:
    scopes_raw = os.getenv("CLAWDBOT_SCOPES", "").strip()
    if not scopes_raw:
        return None
    scopes = [scope for scope in scopes_raw.replace(",", " ").split() if scope]
    return scopes or None


def _get_wait_timeout() -> Optional[float]:
    raw = os.getenv("CLAWDBOT_WAIT_TIMEOUT", "").strip()
    if not raw:
        return 60.0
    try:
        value = float(raw)
        return value if value > 0 else None
    except ValueError:
        logger.warning("Invalid CLAWDBOT_WAIT_TIMEOUT value %s, using default", raw)
        return 60.0


async def send_clawdbot_message(text: str, group_id: str) -> str:
    """
    Send text to Clawdbot gateway and return final reply text.

    Args:
        text: Message text from QQ
        group_id: QQ group ID (used to derive session key if not set explicitly)
    """
    token = os.getenv("CLAWDBOT_TOKEN", "").strip()
    password = os.getenv("CLAWDBOT_PASSWORD", "").strip()
    if not token and not password:
        raise ValueError("CLAWDBOT_TOKEN or CLAWDBOT_PASSWORD must be set when CLAWDBOT_ENABLED is true")

    url = os.getenv("CLAWDBOT_URL", "ws://127.0.0.1:18789").strip()
    session_key = os.getenv("CLAWDBOT_SESSION_KEY", "").strip() or f"qq-group-{group_id}"
    wait_timeout = _get_wait_timeout()
    scopes = _parse_scopes()

    logger.info("Sending message to Clawdbot session=%s url=%s", session_key, url)

    try:
        result = await chat_once_async(
            session_key=session_key,
            message=text,
            url=url,
            token=token or None,
            password=password or None,
            scopes=scopes,
            wait_timeout=wait_timeout,
        )
    except Exception as exc:
        logger.error("Clawdbot request failed: %s", exc, exc_info=True)
        raise

    response_text = (result or {}).get("final_text")
    if response_text:
        return response_text.strip()

    final_payload = (result or {}).get("final")
    if isinstance(final_payload, dict):
        message = final_payload.get("message")
        if isinstance(message, dict):
            content = message.get("content")
            if isinstance(content, list):
                parts = []
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "text" and isinstance(item.get("text"), str):
                        parts.append(item["text"])
                if parts:
                    return "\n".join(parts).strip()

    logger.warning("Clawdbot returned empty response; using fallback text")
    return "Request processed."
