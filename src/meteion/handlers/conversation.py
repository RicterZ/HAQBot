import asyncio
import json
import os
import re
from typing import Dict, Any, Optional, Tuple

from websocket import WebSocketApp

from meteion.clients.homeassistant import HomeAssistantClient
from meteion.utils import CommandEncoder
from meteion.utils.logger import logger
from meteion.models.message import Command, CommandType, TextMessage, ReplyMessage


# Global HA client instance
_ha_client: HomeAssistantClient = None


def is_bot_mentioned(message: dict) -> Tuple[bool, str]:
    """
    Check if bot is mentioned (@) in the message and extract clean text
    
    Args:
        message: QQ message dictionary
        
    Returns:
        Tuple of (is_mentioned, clean_text)
        - is_mentioned: True if bot is mentioned
        - clean_text: Text content with @ mentions removed
    """
    bot_account = os.getenv("ACCOUNT", "").strip()
    if not bot_account:
        return False, ""
    
    message_array = message.get("message", [])
    if isinstance(message_array, list):
        is_mentioned = False
        text_parts = []
        
        for segment in message_array:
            if isinstance(segment, dict):
                seg_type = segment.get("type", "")
                seg_data = segment.get("data", {})
                
                if seg_type == "at":
                    qq = seg_data.get("qq", "")
                    if str(qq) == str(bot_account) or qq == "all":
                        is_mentioned = True
                    continue
                
                elif seg_type == "text":
                    text_content = seg_data.get("text", "")
                    if text_content:
                        text_parts.append(text_content)
        
        clean_text = "".join(text_parts).strip()
        return is_mentioned, clean_text
    
    raw_message = message.get("raw_message", "").strip()
    if not raw_message:
        return False, ""
    
    cq_at_pattern = r'\[CQ:at,qq=(\d+|all)\]'
    matches = re.findall(cq_at_pattern, raw_message)
    
    is_mentioned = False
    for qq in matches:
        if str(qq) == str(bot_account) or qq == "all":
            is_mentioned = True
            break
    
    clean_text = re.sub(cq_at_pattern, "", raw_message).strip()
    clean_text = re.sub(r'@\S+\s*', '', clean_text).strip()
    
    return is_mentioned, clean_text


def get_ha_client() -> HomeAssistantClient:
    """Get or create HA client instance"""
    global _ha_client
    if _ha_client is None:
        _ha_client = HomeAssistantClient()
    return _ha_client


async def process_conversation_async(text: str, language: Optional[str] = None) -> Dict[str, Any]:
    """
    Process conversation request asynchronously
    
    Args:
        text: User input text
        language: Optional language code (e.g., "en", "zh-Hans")
    """
    client = get_ha_client()
    return await client.process_conversation(text, language=language)


def conversation_handler(ws: WebSocketApp, message: dict):
    """
    Handle conversation message
    
    Args:
        ws: WebSocket connection
        message: QQ message dictionary
    """
    group_id = message["group_id"]
    message_id = message.get("message_id")
    
    is_mentioned, clean_text = is_bot_mentioned(message)
    
    if not is_mentioned:
        return
    
    if not clean_text:
        return
    
    logger.info(f"Received conversation message (after removing @): {clean_text}")
    
    try:
        try:
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                raise RuntimeError("Event loop is closed")
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        result = loop.run_until_complete(process_conversation_async(clean_text))
        
        response_text = ""
        response_type = None
        error_code = None
        
        if isinstance(result, dict):
            response = result.get("response", {})
            
            if isinstance(response, dict):
                response_type = response.get("response_type", "unknown")
                if "data" in response and isinstance(response["data"], dict):
                    error_code = response["data"].get("code")
                
                if response_type == "error":
                    logger.warning(f"HA returned an error response (code: {error_code})")
            
            if isinstance(response, dict):
                speech = response.get("speech", {})
                if isinstance(speech, dict):
                    plain = speech.get("plain", {})
                    if isinstance(plain, dict):
                        response_text = plain.get("speech", "")
                    elif isinstance(plain, str):
                        response_text = plain
                elif isinstance(speech, str):
                    response_text = speech
            
            if not response_text and isinstance(response, str):
                response_text = response
            
            if not response_text:
                response_text = result.get("speech", "")
            
            if not response_text:
                response_text = str(result)
                logger.warning(f"Using entire result as response (fallback)")
        else:
            response_text = str(result)
        
        if not response_text or response_text.strip() == "":
            logger.warning("Response text is empty, using default message")
            response_text = "Request processed"
        
        if response_type == "error":
            if error_code == "no_intent_match":
                logger.warning("HA conversation agent could not match user intent")
            else:
                logger.warning(f"HA conversation agent returned error code: {error_code}")
        
        logger.info(f"Conversation response: {response_text[:100]}{'...' if len(response_text) > 100 else ''}")
        
        message_segments = []
        if message_id:
            message_segments.append(ReplyMessage(message_id))
        message_segments.append(TextMessage(response_text))
        command = Command(
            action=CommandType.send_group_msg,
            params={
                "group_id": group_id,
                "message": [msg.as_dict() for msg in message_segments]
            }
        )
        ws.send(json.dumps(command, cls=CommandEncoder))
        
    except Exception as e:
        logger.error(f"Error processing conversation: {e}", exc_info=True)
        error_msg = f"Error processing request: {str(e)}"
        message_segments = []
        if message_id:
            message_segments.append(ReplyMessage(message_id))
        message_segments.append(TextMessage(error_msg))
        
        command = Command(
            action=CommandType.send_group_msg,
            params={
                "group_id": group_id,
                "message": [msg.as_dict() for msg in message_segments]
            }
        )
        ws.send(json.dumps(command, cls=CommandEncoder))

