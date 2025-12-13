import json
import os
import uuid
from typing import Optional, List

from websocket import WebSocketApp

from meteion.models.message import Command, CommandType, TextMessage, VideoMessage, ForwardNode
from meteion.utils import CommandEncoder
from meteion.utils.logger import logger
from meteion.bot.connection import get_ws_connection


def send_group_message(group_id: str, message: str) -> bool:
    """
    Send a message to a QQ group
    
    Args:
        group_id: QQ group ID
        message: Message text to send
        
    Returns:
        True if message was sent successfully, False otherwise
    """
    ws = get_ws_connection()
    if not ws:
        logger.error("WebSocket connection not available")
        return False
    
    try:
        command = Command(
            action=CommandType.send_group_msg,
            params={
                "group_id": group_id,
                "message": TextMessage(message)
            }
        )
        
        ws.send(json.dumps(command, cls=CommandEncoder))
        logger.info(f"Sent message to group {group_id}: {message[:50]}...")
        return True
    except Exception as e:
        logger.error(f"Failed to send message: {e}")
        return False


def send_group_multimodal_message(
    group_id: str, 
    text: Optional[str] = None, 
    file_path: Optional[str] = None,
    event: Optional[str] = None,
    timestamp: Optional[str] = None,
    source: Optional[str] = None,
    nickname: Optional[str] = None
) -> bool:
    """
    Send a multimodal message (text + video) to a QQ group as a forward message
    Uses send_group_forward_msg API to create a card-like message
    
    Args:
        group_id: QQ group ID
        text: Optional message text
        file_path: Optional video file path to send
        event: Optional event name/title (shown in prompt, auto-generated if not provided)
        timestamp: Optional timestamp (shown in summary, auto-generated if not provided)
        source: Optional title/source (default: "Home Assistant")
        nickname: Optional display nickname (default: "Home Assistant")
        
    Returns:
        True if message was sent successfully, False otherwise
    """
    ws = get_ws_connection()
    if not ws:
        logger.error("WebSocket connection not available")
        return False
    
    if not text and not file_path:
        logger.error("At least one of text or file_path must be provided")
        return False
    
    try:
        user_id = os.getenv('ACCOUNT', '1145141919')
        # Ensure user_id is string or number
        try:
            user_id = int(user_id)
        except ValueError:
            pass  # Keep as string
        
        # Build message content array with message objects (not dicts)
        # CommandEncoder will handle serialization
        content: List = []
        if text:
            content.append(TextMessage(text))
        if file_path:
            content.append(VideoMessage(file_path))
        
        display_nickname = nickname or "Home Assistant"
        
        # Create forward node using ForwardNode class
        # content contains message objects, ForwardNode.as_dict() will serialize them
        node = ForwardNode(
            user_id=user_id,
            nickname=display_nickname,
            content=content
        )
        
        from datetime import datetime
        
        news = []
        if event:
            news.append({"text": event})
        if timestamp:
            news.append({"text": timestamp})
        elif event:
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            news.append({"text": current_time})
        
        if not event:
            if text:
                # Use first line as event name
                event = text.split('\n')[0]
                event = event[:30] + "..." if len(event) > 30 else event
            else:
                event = "视频消息"
        prompt = event
        
        if not timestamp:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        summary = timestamp
        
        if not source:
            source = "Home Assistant"
        
        # Build params dict - use node object, CommandEncoder will serialize it
        params = {
            "group_id": group_id,
            "messages": [node],  # ForwardNode object, will be serialized by CommandEncoder
            "news": news,
            "prompt": prompt,
            "summary": summary,
            "source": source
        }
        
        # Use Command and CommandEncoder like the reference code
        command = Command(
            action=CommandType.send_group_forward_msg,
            params=params
        )
        
        # Serialize using CommandEncoder (handles nested objects properly)
        command_json = json.dumps(command, cls=CommandEncoder)
        logger.info(f"Forward message JSON: {command_json}")
        
        ws.send(command_json)
        logger.info(f"Sent forward message to group {group_id}: text={text[:50] if text else None}, video={file_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to send forward message: {e}")
        return False

