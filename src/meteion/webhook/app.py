import os
from typing import Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from meteion.services.sender import send_group_message, send_group_multimodal_message
from meteion.utils.logger import logger
from meteion.utils.video import download_video_stream_async


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
    # Forward message display options
    event: Optional[str] = None  # Event name/title (shown in prompt)
    timestamp: Optional[str] = None  # Timestamp (shown in summary)
    source: Optional[str] = None  # Source/title
    nickname: Optional[str] = None  # Display nickname


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
    
    # Process video stream if URL is provided
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
                    detail="Failed to download video stream"
                )
            
            logger.info(f"Video stream downloaded to: {file_path}")
        except Exception as e:
            logger.error(f"Error processing video stream: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to process video stream: {str(e)}"
            )
    
    # Send multimodal message
    success = send_group_multimodal_message(
        group_id=request.group_id,
        text=request.message,
        file_path=file_path,
        event=request.event,
        timestamp=request.timestamp,
        source=request.source,
        nickname=request.nickname
    )
    
    if success:
        # Clean up temporary file if it was created
        if file_path and os.path.exists(file_path):
            try:
                # Note: We don't delete immediately as the file might still be in use
                # In production, you might want to implement a cleanup job
                pass
            except Exception as e:
                logger.warning(f"Failed to cleanup temp file {file_path}: {e}")
        
        return {
            "status": "ok",
            "message": "Multimodal notification sent",
            "file_path": file_path
        }
    else:
        # Clean up on failure
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

