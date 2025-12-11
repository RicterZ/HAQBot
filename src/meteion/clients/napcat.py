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
    api_url = f"{base_url}/get_record"
    
    payload = {"file": file, "out_format": out_format}
    logger.info(f"请求 NapCat 语音文件: {payload}")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.post(api_url, json=payload)
            resp.raise_for_status()
        except Exception as exc:
            logger.error(f"请求 NapCat get_record 失败: {exc}")
            raise RuntimeError("无法请求 NapCat 获取语音文件") from exc
        
        try:
            result = resp.json()
        except Exception as exc:
            logger.error(f"解析 NapCat 响应失败: {exc}")
            raise RuntimeError("NapCat 返回了无法解析的响应") from exc
        
        status = result.get("status")
        retcode = result.get("retcode")
        if status not in ("ok", "OK") and retcode not in (0, None):
            logger.error(f"NapCat get_record 返回错误: {result}")
            raise RuntimeError("NapCat 获取语音文件失败")
        
        record_file = None
        data = result.get("data") or {}
        if isinstance(data, dict):
            record_file = data.get("file") or data.get("url")
        
        if not record_file:
            logger.error(f"NapCat 响应中缺少文件信息: {result}")
            raise RuntimeError("NapCat 未返回有效的语音文件地址")
        
        # 组装可下载的 URL
        if record_file.startswith("http://") or record_file.startswith("https://"):
            download_url = record_file
        else:
            download_url = f"{base_url}/{record_file.lstrip('/')}"
        
        try:
            file_resp = await client.get(download_url)
            file_resp.raise_for_status()
        except Exception as exc:
            logger.error(f"下载语音文件失败: {download_url}, 错误: {exc}")
            raise RuntimeError("无法下载语音文件") from exc
        
        return file_resp.content

