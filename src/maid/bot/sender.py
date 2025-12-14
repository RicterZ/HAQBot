"""Message sender for QQ bot - used by webhook to send proactive messages"""
import json
import os
from typing import Optional, List

from maid.models.message import Command, CommandType, TextMessage, FileMessage, ForwardNode
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
    message: Optional[str] = None, 
    file_path: Optional[str] = None,
) -> bool:
    """
    Send a multimodal message (text + file) to a QQ group as a forward message
    Uses send_group_forward_msg API to create a card-like message
    
    Args:
        group_id: QQ group ID
        message: Optional message text
        file_path: Optional file path to send (video or other files)
        
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
            file_node = ForwardNode(
                user_id=user_id,
                nickname=display_nickname,
                content=[FileMessage(file_path)]
            )
            nodes.append(file_node)
            logger.info(f"Sending file message: {file_path}")
        
        time_node = ForwardNode(
            user_id=user_id,
            nickname=display_nickname,
            content=[TextMessage(timestamp)]
        )
        nodes.append(time_node)
        source = f"{display_nickname} WARNING"
        
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
        logger.info(f"Sent forward message to group {group_id}: message={message[:50] if message else None}, file={file_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to send forward message: {e}")
        return False

