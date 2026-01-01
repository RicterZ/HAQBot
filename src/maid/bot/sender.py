"""Message sender for QQ bot - used by webhook to send proactive messages"""
import json
import os
from typing import Optional, List, Literal

from maid.models.message import (
    Command, CommandType, TextMessage, FileMessage, ImageMessage, 
    VideoMessage, ForwardNode
)
from maid.utils import CommandEncoder
from maid.utils.logger import logger
from maid.utils.i18n import t
from maid.bot.connection import get_ws_connection


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
        logger.error(t("websocket_not_available"))
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
    title: Optional[str] = None,
    message: Optional[str] = None, 
    file_path: Optional[str] = None,
    file_type: Optional[Literal["image", "video", "file"]] = None,
) -> bool:
    """
    Send a multimodal message (text + file/image/video) to a QQ group as a forward message
    Uses send_group_forward_msg API to create a card-like message
    
    Args:
        group_id: QQ group ID
        title: Optional title text
        message: Optional message text
        file_path: Optional file path to send (video, image, or other files)
        file_type: Optional file type ("image", "video", or "file"). If not provided, will be inferred from file_path
        
    Returns:
        True if message was sent successfully, False otherwise
    """
    ws = get_ws_connection()
    if not ws:
        logger.error(t("websocket_not_available"))
        return False
    
    if not message and not file_path:
        logger.error(t("message_or_file_required"))
        return False
    
    try:
        from datetime import datetime
        
        user_id = os.getenv('ACCOUNT', '10001')
        display_nickname = os.getenv('DISPLAY_NICKNAME', 'メイド')
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        nodes: List[ForwardNode] = []
        
        if message:
            text_node = ForwardNode(
                user_id=user_id,
                nickname=display_nickname,
                content=[TextMessage(message)]
            )
            nodes.append(text_node)
        
        if file_path:
            # Determine file type if not provided
            if file_type is None:
                file_lower = file_path.lower()
                if any(file_lower.endswith(ext) for ext in ('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg', '.ico')):
                    file_type = "image"
                elif any(file_lower.endswith(ext) for ext in ('.mp4', '.avi', '.mov', '.mkv', '.flv', '.webm', '.m4v')):
                    file_type = "video"
                else:
                    file_type = "file"
            
            # Create appropriate message type
            if file_type == "image":
                file_node = ForwardNode(
                    user_id=user_id,
                    nickname=display_nickname,
                    content=[ImageMessage(file_path)]
                )
                logger.info(f"Sending image message: {file_path}")
            elif file_type == "video":
                file_node = ForwardNode(
                    user_id=user_id,
                    nickname=display_nickname,
                    content=[FileMessage(file_path)] # use FileMessage instead of VideoMessage
                )
                logger.info(f"Sending video message: {file_path}")
            else:
                file_node = ForwardNode(
                    user_id=user_id,
                    nickname=display_nickname,
                    content=[FileMessage(file_path)]
                )
                logger.info(f"Sending file message: {file_path}")
            
            nodes.append(file_node)
        
        source = title or f"{display_nickname} WARNING"
        
        message_text = message or ""
        news = [{"text": message_text}]
        params = {
            "group_id": group_id,
            "messages": nodes,
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
        logger.info(f"Sent forward message to group {group_id}: message={message[:50] if message else None}, file={file_path}, type={file_type}")
        return True
    except Exception as e:
        logger.error(f"Failed to send forward message: {e}")
        return False

