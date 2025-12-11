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
        response_raw = ws.recv()
    except Exception as exc:
        ws.close()
        logger.error(f"Failed to send/receive get_record via websocket: {exc}")
        raise RuntimeError("Failed to request NapCat for voice file via websocket") from exc
    finally:
        ws.close()
    
    try:
        result = json.loads(response_raw)
    except Exception as exc:
        logger.error(f"Failed to parse NapCat websocket response: {exc}")
        raise RuntimeError("NapCat returned an unparseable websocket response") from exc
    
    if result.get("echo") != echo:
        logger.warning(f"Echo mismatch for get_record response: {result}")
    
    status = result.get("status")
    retcode = result.get("retcode")
    if status not in ("ok", "OK") and retcode not in (0, None):
        logger.error(f"NapCat get_record returned error: {result}")
        raise RuntimeError("NapCat failed to provide voice file")
    
    record_file = None
    data = result.get("data") or {}
    if isinstance(data, dict):
        record_file = data.get("file") or data.get("url")
    
    if not record_file:
        logger.error(f"NapCat response missing file info: {result}")
        raise RuntimeError("NapCat did not return a valid voice file path")
    
    if record_file.startswith("http://") or record_file.startswith("https://"):
        download_url = record_file
    else:
        download_url = f"{base_url}/{record_file.lstrip('/')}"
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            file_resp = await client.get(download_url)
            file_resp.raise_for_status()
        except Exception as exc:
            logger.error(f"Failed to download voice file: {download_url}, error: {exc}")
            raise RuntimeError("Unable to download voice file") from exc
        
        return file_resp.content

