"""Natural language conversation handler"""
import re
import threading
from typing import Dict, Any, Optional, Tuple

from websocket import WebSocketApp

from maid.clients.homeassistant import HomeAssistantClient
from maid.clients.napcat import get_voice_file
from maid.clients.tencent_asr import sentence_recognize
from maid.utils.logger import logger
from maid.utils.i18n import t
from maid.utils.response import send_response, run_async_task


_conversation_ids: Dict[str, Optional[str]] = {}
_conversation_lock = threading.Lock()


def clear_conversation_context(group_id: str):
    """Clear conversation context for a group
    
    Args:
        group_id: QQ group ID
    
    Returns:
        True if context was cleared, False if no context existed
    """
    with _conversation_lock:
        if group_id in _conversation_ids:
            del _conversation_ids[group_id]
            logger.info(f"Cleared conversation context for group {group_id}")
            return True
    return False


def extract_message_content(message: dict) -> Tuple[str, Optional[str]]:
    """Extract text content and voice file from message
    
    Args:
        message: Message dictionary from WebSocket
    
    Returns:
        Tuple of (clean_text, record_file)
    """
    message_array = message.get("message", [])
    if isinstance(message_array, list):
        text_parts = []
        record_file = None
        
        for segment in message_array:
            if isinstance(segment, dict):
                seg_type = segment.get("type", "")
                seg_data = segment.get("data", {})
                
                if seg_type == "at":
                    continue
                elif seg_type == "text":
                    text_content = seg_data.get("text", "")
                    if text_content:
                        text_parts.append(text_content)
                elif seg_type == "record" and record_file is None:
                    record_file = seg_data.get("file")
        
        clean_text = "".join(text_parts).strip()
        return clean_text, record_file
    
    raw_message = message.get("raw_message", "").strip()
    if not raw_message:
        return "", None
    
    cq_at_pattern = r'\[CQ:at,qq=(\d+|all)\]'
    clean_text = re.sub(cq_at_pattern, "", raw_message).strip()
    clean_text = re.sub(r'@\S+\s*', '', clean_text).strip()
    
    return clean_text, None


async def process_conversation_async(text: str, group_id: str, language: Optional[str] = None) -> Dict[str, Any]:
    """Process conversation asynchronously
    
    Args:
        text: User input text
        group_id: QQ group ID
        language: Optional language code
    
    Returns:
        Conversation result dictionary
    """
    with _conversation_lock:
        conversation_id = _conversation_ids.get(group_id)
    
    client = HomeAssistantClient()
    try:
        result = await client.process_conversation(text, language=language, conversation_id=conversation_id)
        
        if isinstance(result, dict) and "conversation_id" in result:
            new_conversation_id = result["conversation_id"]
            with _conversation_lock:
                _conversation_ids[group_id] = new_conversation_id
        
        return result
    finally:
        await client.close()


async def _process_conversation_task(ws: WebSocketApp, group_id: str, message_id: Optional[str], clean_text: Optional[str], record_file: Optional[str]):
    """Async task: process conversation message"""
    try:
        if not clean_text and record_file:
            try:
                audio_bytes = await get_voice_file(record_file, out_format="mp3")
                clean_text = await sentence_recognize(audio_bytes, voice_format="mp3")
                logger.info(f"ASR transcribed voice to text: {clean_text}")
            except Exception as exc:
                logger.warning(f"ASR failed, skip replying: {exc}")
                return
        
        if not clean_text:
            return
        
        logger.info(f"Received conversation message (after removing @): {clean_text}")
        
        result = await process_conversation_async(clean_text, group_id)
        
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
            response_text = t("request_processed")
        
        if response_type == "error":
            if error_code == "no_intent_match":
                logger.warning("HA conversation agent could not match user intent")
            else:
                logger.warning(f"HA conversation agent returned error code: {error_code}")
        
        logger.info(f"Conversation response: {response_text[:100]}{'...' if len(response_text) > 100 else ''}")
        
        send_response(ws, group_id, message_id, response_text)
        
    except Exception as e:
        logger.error(f"Error processing conversation: {e}", exc_info=True)
        error_msg = t("error_processing_request", error=str(e))
        send_response(ws, group_id, message_id, error_msg)


def conversation_handler(ws: WebSocketApp, message: dict):
    """Handle natural language conversation messages
    
    Args:
        ws: WebSocket connection
        message: Message dictionary from WebSocket
    """
    group_id = message["group_id"]
    message_id = message.get("message_id")
    
    clean_text, record_file = extract_message_content(message)
    
    if not clean_text and not record_file:
        return
    
    task = _process_conversation_task(ws, group_id, message_id, clean_text, record_file)
    thread = threading.Thread(target=run_async_task, args=(task,), daemon=True)
    thread.start()

