import asyncio
import os
import threading
import uuid
from typing import Optional, List, Dict, Any

from moltbot import GatewayWebSocketClient, GatewayError

from maid.utils.logger import logger
from maid.utils.i18n import t


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


def _extract_text(payload: Dict[str, Any]) -> Optional[str]:
    message = payload.get("message") if isinstance(payload, dict) else None
    if not isinstance(message, dict):
        return None
    content = message.get("content")
    if not isinstance(content, list):
        return None
    parts = []
    for item in content:
        if isinstance(item, dict) and item.get("type") == "text" and isinstance(item.get("text"), str):
            parts.append(item["text"])
    return "\n".join(parts) if parts else None


class _ClawdbotManager:
    """Maintain a single long-lived gateway client with auto-reconnect."""

    def __init__(self) -> None:
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

        self._client: Optional[GatewayWebSocketClient] = None
        self._waiters: Dict[str, asyncio.Future] = {}

        self._config = self._load_config()

    def _run_loop(self) -> None:
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    def _load_config(self) -> Dict[str, Any]:
        token = os.getenv("CLAWDBOT_TOKEN", "").strip()
        password = os.getenv("CLAWDBOT_PASSWORD", "").strip()
        if not token and not password:
            raise ValueError("CLAWDBOT_TOKEN or CLAWDBOT_PASSWORD must be set when CLAWDBOT_ENABLED is true")

        return {
            "url": os.getenv("CLAWDBOT_URL", "ws://127.0.0.1:18789").strip(),
            "token": token or None,
            "password": password or None,
            "session_key": os.getenv("CLAWDBOT_SESSION_KEY", "").strip(),
            "wait_timeout": _get_wait_timeout(),
            "scopes": _parse_scopes(),
        }

    async def _ensure_client(self) -> GatewayWebSocketClient:
        if self._client and not getattr(self._client, "_closed", False):
            return self._client

        # Build a new client and connect
        self._client = GatewayWebSocketClient(
            url=self._config["url"],
            token=self._config["token"],
            password=self._config["password"],
            scopes=self._config["scopes"],
            on_event=self._on_event,
            on_close=self._on_close,
        )
        await self._client.connect()
        logger.info("Clawdbot gateway connected")
        return self._client

    def _on_close(self, code: int, reason: str) -> None:
        logger.warning("Clawdbot gateway closed: %s %s", code, reason)
        self._client = None

    def _on_event(self, frame: Dict[str, Any]) -> None:
        if frame.get("event") != "chat":
            return
        payload = frame.get("payload") or {}
        run_id = payload.get("runId")
        state = payload.get("state")
        if not isinstance(run_id, str):
            return
        waiter = self._waiters.get(run_id)
        if not waiter:
            return
        if state in {"final", "error", "aborted"}:
            if not waiter.done():
                waiter.set_result(payload)

    async def _send_once(self, text: str, group_id: str) -> str:
        client = await self._ensure_client()
        session_key = self._config["session_key"] or f"qq-group-{group_id}"
        wait_timeout = self._config["wait_timeout"]

        run_id = str(uuid.uuid4())
        fut: asyncio.Future = self._loop.create_future()
        self._waiters[run_id] = fut

        try:
            await client.send_chat(
                session_key=session_key,
                message=text,
                idempotency_key=run_id,
            )
            payload: Dict[str, Any] = await asyncio.wait_for(fut, timeout=wait_timeout)  # type: ignore
            response_text = _extract_text(payload) or ""
            return response_text.strip() or t("request_processed")
        except asyncio.TimeoutError:
            logger.warning("Clawdbot wait timed out run_id=%s", run_id)
            return t("request_processed")
        except GatewayError as exc:
            logger.error("Clawdbot gateway error: %s", exc)
            self._client = None
            raise
        except Exception as exc:
            logger.error("Clawdbot request failed: %s", exc, exc_info=True)
            self._client = None
            raise
        finally:
            self._waiters.pop(run_id, None)

    def submit(self, text: str, group_id: str) -> "asyncio.Future[str]":
        return asyncio.run_coroutine_threadsafe(self._send_once(text, group_id), self._loop)  # type: ignore


_manager: Optional[_ClawdbotManager] = None
_manager_lock = threading.Lock()


def _get_manager() -> _ClawdbotManager:
    global _manager
    if _manager is None:
        with _manager_lock:
            if _manager is None:
                _manager = _ClawdbotManager()
    return _manager


async def send_clawdbot_message(text: str, group_id: str) -> str:
    """
    Send text to Clawdbot gateway via a persistent connection and return final reply text.
    """
    mgr = _get_manager()
    cf = mgr.submit(text, group_id)
    return await asyncio.wrap_future(cf)  # type: ignore
