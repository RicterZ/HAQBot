import json
from typing import Optional, List

from websocket import WebSocketApp

from meteion.models.message import Command, CommandType, TextMessage, FileMessage
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


def send_group_multimodal_message(group_id: str, text: Optional[str] = None, file_path: Optional[str] = None) -> bool:
    """
    Send a multimodal message (text + file) to a QQ group
    
    Args:
        group_id: QQ group ID
        text: Optional message text
        file_path: Optional file path or URL to send
        
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
        message_segments: List = []
        
        if text:
            message_segments.append(TextMessage(text))
        
        if file_path:
            message_segments.append(FileMessage(file_path))
        
        command = Command(
            action=CommandType.send_group_msg,
            params={
                "group_id": group_id,
                "message": [msg.as_dict() for msg in message_segments]
            }
        )
        
        ws.send(json.dumps(command, cls=CommandEncoder))
        logger.info(f"Sent multimodal message to group {group_id}: text={text[:50] if text else None}, file={file_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to send multimodal message: {e}")
        return False

