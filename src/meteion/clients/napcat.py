import os
from urllib.parse import urlparse

import httpx

from meteion.utils.logger import logger


def _build_http_base_url() -> str:
    raw = os.getenv("NAPCAT_API", "ws://napcat:3001")
    parsed = urlparse(raw)
    
    if parsed.scheme in ("ws", "wss"):
        scheme = "http" if parsed.scheme == "ws" else "https"
    elif parsed.scheme in ("http", "https"):
        scheme = parsed.scheme
    else:
        # 默认退回 http
        scheme = "http"
    
    hostname = parsed.hostname or "napcat"
    port = parsed.port
    
    if not port:
        port = 80 if scheme == "http" else 443
    
    return f"{scheme}://{hostname}:{port}"


async def get_voice_file(file: str, out_format: str = "mp3") -> bytes:
    base_url = _build_http_base_url()
    api_url = base_url
    
    payload = {"file": file, "out_format": out_format}
    request_body = {"action": "get_record", "params": payload}
    logger.info(f"Requesting NapCat voice file via action: {request_body}")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.post(api_url, json=request_body)
            resp.raise_for_status()
        except Exception as exc:
            logger.error(f"NapCat get_record request failed: {exc}")
            raise RuntimeError("Failed to request NapCat for voice file") from exc
        
        try:
            result = resp.json()
        except Exception as exc:
            logger.error(f"Failed to parse NapCat response: {exc}")
            raise RuntimeError("NapCat returned an unparseable response") from exc
        
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
        
        # 组装可下载的 URL
        if record_file.startswith("http://") or record_file.startswith("https://"):
            download_url = record_file
        else:
            download_url = f"{base_url}/{record_file.lstrip('/')}"
        
        try:
            file_resp = await client.get(download_url)
            file_resp.raise_for_status()
        except Exception as exc:
            logger.error(f"Failed to download voice file: {download_url}, error: {exc}")
            raise RuntimeError("Unable to download voice file") from exc
        
        return file_resp.content

