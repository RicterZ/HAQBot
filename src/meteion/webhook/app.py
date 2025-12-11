import os
from typing import Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from meteion.services.sender import send_group_message
from meteion.utils.logger import logger


app = FastAPI(title="Home Assistant QQ Bot Webhook")


class WebhookRequest(BaseModel):
    group_id: str
    message: str
    token: Optional[str] = None


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


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "ok"}

