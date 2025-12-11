import base64
import json
import os
import uuid
from urllib.parse import urlparse

import httpx
from websocket import create_connection

from meteion.utils.logger import logger


async def get_voice_file(file: str, out_format: str = "mp3") -> bytes:
    raw = os.getenv("NAPCAT_API", "ws://napcat:3001")
    parsed = urlparse(raw)
    if parsed.scheme in ("ws", "wss"):
        scheme = "http" if parsed.scheme == "ws" else "https"
    else:
        scheme = parsed.scheme or "http"
    hostname = parsed.hostname or "napcat"
    port = parsed.port or (80 if scheme == "http" else 443)
    base_url = f"{scheme}://{hostname}:{port}"
    ws_url = raw
    
    payload = {"file": file, "out_format": out_format}
    echo = str(uuid.uuid4())
    request_body = {"action": "get_record", "params": payload, "echo": echo}
    logger.info(f"Requesting NapCat voice file via websocket action: {request_body}")
    
    try:
        ws = create_connection(ws_url, timeout=15)
    except Exception as exc:
        logger.error(f"Failed to open websocket to NapCat: {exc}")
        raise RuntimeError("Cannot connect to NapCat websocket") from exc
    
    try:
        ws.send(json.dumps(request_body))
        response = None
        for _ in range(5):
            try:
                response_raw = ws.recv()
            except Exception as exc:
                logger.error(f"Failed to receive get_record via websocket: {exc}")
                break
            try:
                candidate = json.loads(response_raw)
            except Exception:
                continue
            if not isinstance(candidate, dict):
                continue
            # Skip meta_event or unrelated messages
            if candidate.get("post_type") == "meta_event":
                continue
            if candidate.get("echo") and candidate.get("echo") != echo:
                continue
            if not candidate.get("status"):
                continue
            response = candidate
            break
    except Exception as exc:
        ws.close()
        logger.error(f"Failed to send/receive get_record via websocket: {exc}")
        raise RuntimeError("Failed to request NapCat for voice file via websocket") from exc
    finally:
        ws.close()
    
    if response is None:
        raise RuntimeError("NapCat did not return get_record response")
    
    status = response.get("status")
    retcode = response.get("retcode")
    if status not in ("ok", "OK") and retcode not in (0, None):
        logger.error(f"NapCat get_record returned error: {response}")
        raise RuntimeError("NapCat failed to provide voice file")
    
    record_file = None
    record_url = None
    record_base64 = None
    data = response.get("data") or {}
    if isinstance(data, dict):
        record_url = data.get("url")
        record_file = data.get("file")
        record_base64 = data.get("base64")
    
    if record_base64:
        try:
            return base64.b64decode(record_base64)
        except Exception as exc:
            logger.error(f"Failed to decode base64 voice data: {exc}")
            raise RuntimeError("NapCat returned invalid base64 voice data") from exc
    
    target = record_url or record_file
    if not target:
        logger.error(f"NapCat response missing file/url/base64: {response}")
        raise RuntimeError("NapCat did not return a valid voice file path")
    
    if target.startswith("http://") or target.startswith("https://"):
        download_url = target
    else:
        download_url = f"{base_url}/{target.lstrip('/')}"
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            file_resp = await client.get(download_url)
            file_resp.raise_for_status()
        except Exception as exc:
            logger.error(f"Failed to download voice file: {download_url}, error: {exc}")
            raise RuntimeError("Unable to download voice file") from exc
        
        return file_resp.content

