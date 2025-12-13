import os
from typing import Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from meteion.services.sender import send_group_message, send_group_multimodal_message
from meteion.utils.logger import logger
from meteion.utils.video import download_video_stream_async, convert_video_to_gif_async


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
        raise HTTPException(status_code=401, detail="Invalid webhook token")
    
    if not request.group_id or not request.message:
        raise HTTPException(status_code=400, detail="group_id and message are required")
    
    success = send_group_message(request.group_id, request.message)
    
    if success:
        return {"status": "ok", "message": "Notification sent"}
    else:
        raise HTTPException(status_code=500, detail="Failed to send notification")


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
        raise HTTPException(status_code=401, detail="Invalid webhook token")
    
    if not request.group_id:
        raise HTTPException(status_code=400, detail="group_id is required")
    
    if not request.message and not request.url:
        raise HTTPException(status_code=400, detail="At least one of message or url is required")
    
    file_path = None
    
    video_path = None
    file_path = None
    
    if request.url:
        try:
            logger.info(f"Processing video stream from URL: {request.url}")
            video_path = await download_video_stream_async(
                request.url,
                duration=request.duration or 60
            )
            
            if not video_path:
                raise HTTPException(
                    status_code=500,
                    detail="Failed to download video stream"
                )
            
            logger.info(f"Video stream downloaded to: {video_path}")
            
            logger.info(f"Converting video to GIF: {video_path}")
            file_path = await convert_video_to_gif_async(video_path)
            
            if not file_path:
                raise HTTPException(
                    status_code=500,
                    detail="Failed to convert video to GIF"
                )
            
            logger.info(f"Video converted to GIF: {file_path}")
            
            if video_path and os.path.exists(video_path):
                try:
                    os.remove(video_path)
                    logger.info(f"Cleaned up video file: {video_path}")
                except Exception as e:
                    logger.warning(f"Failed to cleanup video file {video_path}: {e}")
        except Exception as e:
            logger.error(f"Error processing video stream: {e}")
            if video_path and os.path.exists(video_path):
                try:
                    os.remove(video_path)
                except:
                    pass
            if file_path and os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except:
                    pass
            raise HTTPException(
                status_code=500,
                detail=f"Failed to process video stream: {str(e)}"
            )
    
    success = send_group_multimodal_message(
        group_id=request.group_id,
        message=request.message,
        file_path=file_path
    )
    
    if success:
        return {
            "status": "ok",
            "message": "Multimodal notification sent",
            "file_path": file_path
        }
    else:
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except:
                pass
        raise HTTPException(status_code=500, detail="Failed to send multimodal notification")


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "ok"}

