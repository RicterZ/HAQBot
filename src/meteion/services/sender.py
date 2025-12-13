import json
import os
from typing import Optional, List

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
    message: Optional[str] = None, 
    file_path: Optional[str] = None,
) -> bool:
    """
    Send a multimodal message (text + video) to a QQ group as a forward message
    Uses send_group_forward_msg API to create a card-like message
    
    Args:
        group_id: QQ group ID
        message: Optional message text
        file_path: Optional video file path to send
        
    Returns:
        True if message was sent successfully, False otherwise
    """
    ws = get_ws_connection()
    if not ws:
        logger.error("WebSocket connection not available")
        return False
    
    if not message and not file_path:
        logger.error("At least one of message or file_path must be provided")
        return False
    
    try:
        from datetime import datetime
        
        user_id = os.getenv('ACCOUNT', '1145141919')
        display_nickname = "メイド"
        
        content: List = []
        if file_path:
            content.append(VideoMessage(file_path))
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        source = "メイド WARNING"
        
        node = ForwardNode(
            user_id=user_id,
            nickname=display_nickname,
            content=content
        )
        
        message_text = message or "视频消息"
        news = [{"text": message_text}]
        params = {
            "group_id": group_id,
            "messages": [node],
            "news": news,
            "prompt": message_text,
            "summary": timestamp,
            "source": source
        }
        
        command = Command(
            action=CommandType.send_group_forward_msg,
            params=params
        )
        
        command_json = json.dumps(command, cls=CommandEncoder)
        logger.info(f"Forward message JSON: {command_json}")
        
        ws.send(command_json)
        logger.info(f"Sent forward message to group {group_id}: message={message[:50] if message else None}, video={file_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to send forward message: {e}")
        return False

