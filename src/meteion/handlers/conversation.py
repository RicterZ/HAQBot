import asyncio
import json
import os
import re
import threading
from typing import Dict, Any, Optional, Tuple

from websocket import WebSocketApp

from meteion.clients.homeassistant import HomeAssistantClient
from meteion.clients.napcat import get_voice_file
from meteion.clients.tencent_asr import sentence_recognize
from meteion.utils import CommandEncoder
from meteion.utils.logger import logger
from meteion.models.message import Command, CommandType, TextMessage, ReplyMessage


_ha_client: HomeAssistantClient = None


def is_bot_mentioned(message: dict) -> Tuple[bool, str, Optional[str]]:
    bot_account = os.getenv("ACCOUNT", "").strip()
    if not bot_account:
        return False, "", None
    
    message_array = message.get("message", [])
    if isinstance(message_array, list):
        is_mentioned = False
        text_parts = []
        record_file = None
        
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
                
                elif seg_type == "record" and record_file is None:
                    record_file = seg_data.get("file")
        
        clean_text = "".join(text_parts).strip()
        return is_mentioned, clean_text, record_file
    
    raw_message = message.get("raw_message", "").strip()
    if not raw_message:
        return False, "", None
    
    cq_at_pattern = r'\[CQ:at,qq=(\d+|all)\]'
    matches = re.findall(cq_at_pattern, raw_message)
    
    is_mentioned = False
    for qq in matches:
        if str(qq) == str(bot_account) or qq == "all":
            is_mentioned = True
            break
    
    clean_text = re.sub(cq_at_pattern, "", raw_message).strip()
    clean_text = re.sub(r'@\S+\s*', '', clean_text).strip()
    
    return is_mentioned, clean_text, None


def get_ha_client() -> HomeAssistantClient:
    global _ha_client
    if _ha_client is None:
        _ha_client = HomeAssistantClient()
    return _ha_client


async def process_conversation_async(text: str, language: Optional[str] = None) -> Dict[str, Any]:
    client = get_ha_client()
    return await client.process_conversation(text, language=language)


def _send_response(ws: WebSocketApp, group_id: str, message_id: Optional[str], response_text: str):
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


async def _process_conversation_task(ws: WebSocketApp, group_id: str, message_id: Optional[str], clean_text: Optional[str], record_file: Optional[str]):
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
        
        result = await process_conversation_async(clean_text)
        
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
        
        _send_response(ws, group_id, message_id, response_text)
        
    except Exception as e:
        logger.error(f"Error processing conversation: {e}", exc_info=True)
        error_msg = f"Error processing request: {str(e)}"
        _send_response(ws, group_id, message_id, error_msg)


def _run_async_task(coro):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(coro)
    finally:
        loop.close()


def conversation_handler(ws: WebSocketApp, message: dict):
    group_id = message["group_id"]
    message_id = message.get("message_id")
    
    is_mentioned, clean_text, record_file = is_bot_mentioned(message)
    
    if not is_mentioned and not record_file:
        return
    
    task = _process_conversation_task(ws, group_id, message_id, clean_text, record_file)
    thread = threading.Thread(target=_run_async_task, args=(task,), daemon=True)
    thread.start()

