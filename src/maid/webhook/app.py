import os
from typing import Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from maid.bot.sender import send_group_message, send_group_multimodal_message
from maid.utils.logger import logger
from maid.utils.i18n import t
from maid.utils.video import download_video_stream_async


app = FastAPI(title="Home Assistant QQ Bot Webhook")


class WebhookRequest(BaseModel):
    group_id: str
    message: str
    token: Optional[str] = None


class MultimodalWebhookRequest(BaseModel):
    group_id: str
    message: Optional[str] = None
    url: Optional[str] = None
    token: Optional[str] = None
    duration: Optional[int] = 60  # Video stream duration in seconds


@app.post("/webhook/notify")
async def notify(request: WebhookRequest):
    """
    Webhook endpoint for Home Assistant to send notifications
    
    Request body:
    {
        "group_id": "123456789",
        "message": "Your notification message",
        "token": "optional_webhook_token"
    }
    """
    webhook_token = os.getenv("WEBHOOK_TOKEN", "")
    
    if webhook_token and request.token != webhook_token:
        raise HTTPException(status_code=401, detail=t("invalid_webhook_token"))
    
    if not request.group_id or not request.message:
        raise HTTPException(status_code=400, detail=t("group_id_and_message_required"))
    
    success = send_group_message(request.group_id, request.message)
    
    if success:
        return {"status": "ok", "message": t("notification_sent")}
    else:
        raise HTTPException(status_code=500, detail=t("failed_to_send_notification"))


@app.post("/webhook/multimodal")
async def multimodal_notify(request: MultimodalWebhookRequest):
    """
    Webhook endpoint for sending multimodal messages (text + file/video)
    
    Request body:
    {
        "group_id": "123456789",
        "message": "Optional text message",
        "url": "http://example.com/video_stream.m3u8",
        "token": "optional_webhook_token",
        "duration": 60  // Optional: video stream duration in seconds
    }
    """
    webhook_token = os.getenv("WEBHOOK_TOKEN", "")
    
    if webhook_token and request.token != webhook_token:
        raise HTTPException(status_code=401, detail=t("invalid_webhook_token"))
    
    if not request.group_id:
        raise HTTPException(status_code=400, detail=t("group_id_required"))
    
    if not request.message and not request.url:
        raise HTTPException(status_code=400, detail=t("message_or_url_required"))
    
    file_path = None
    
    if request.url:
        try:
            logger.info(f"Processing video stream from URL: {request.url}")
            file_path = await download_video_stream_async(
                request.url,
                duration=request.duration or 60
            )
            
            if not file_path:
                raise HTTPException(
                    status_code=500,
                    detail=t("failed_to_download_video_stream")
                )
            
            logger.info(f"Video stream downloaded to: {file_path}")
        except Exception as e:
            logger.error(f"Error processing video stream: {e}")
            if file_path and os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except:
                    pass
            raise HTTPException(
                status_code=500,
                detail=t("failed_to_process_video_stream", error=str(e))
            )
    
    success = send_group_multimodal_message(
        group_id=request.group_id,
        message=request.message,
        file_path=file_path
    )
    
    if success:
        return {
            "status": "ok",
            "message": t("multimodal_notification_sent"),
            "file_path": file_path
        }
    else:
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except:
                pass
        raise HTTPException(status_code=500, detail=t("failed_to_send_multimodal_notification"))


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "ok"}

