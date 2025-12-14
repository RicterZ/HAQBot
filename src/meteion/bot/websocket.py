import json
import asyncio
import threading
from typing import Optional, List

from websocket import WebSocketApp

from meteion.utils import CommandEncoder
from meteion.utils.logger import logger
from meteion.utils.i18n import t
from meteion.models.message import Command, CommandType, TextMessage, ReplyMessage
from meteion.handlers.conversation import conversation_handler, clear_conversation_context
from meteion.bot.connection import set_ws_connection
from meteion.clients.homeassistant import HomeAssistantClient


def echo_handler(ws: WebSocketApp, message: dict):
    group_id = message["group_id"]
    resp = message["raw_message"][6:]

    command = Command(action=CommandType.send_group_msg,
                      params={
                          "group_id": group_id,
                          "message": TextMessage(resp)
                      })

    logger.info(f"send command: {command}")
    ws.send(json.dumps(command, cls=CommandEncoder))


def clear_handler(ws: WebSocketApp, message: dict):
    group_id = message["group_id"]
    message_id = message.get("message_id")
    
    cleared = clear_conversation_context(group_id)
    response_text = t("conversation_context_cleared") if cleared else t("no_conversation_context")
    _send_response(ws, group_id, message_id, response_text)


def _send_response(ws: WebSocketApp, group_id: str, message_id: Optional[str], response_text: str):
    """Helper function to send response message"""
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


def _run_async_task(coro):
    """Helper function to run async task in separate thread"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(coro)
    finally:
        loop.close()


def _parse_entity_ids(raw_message: str, command_prefix: str) -> List[str]:
    """Parse entity IDs from command message"""
    if not raw_message.startswith(command_prefix):
        return []
    
    args = raw_message[len(command_prefix):].strip()
    if not args:
        return []
    
    return [eid.strip() for eid in args.split() if eid.strip()]


def _extract_domain(entity_id: str) -> str:
    """Extract domain from entity ID (e.g., 'light.xxx' -> 'light')"""
    if '.' in entity_id:
        return entity_id.split('.')[0]
    return "switch"  # Default fallback


def _get_service_action(service: str) -> str:
    """Get localized service action name"""
    action_map = {
        "turn_on": t("turn_on"),
        "turn_off": t("turn_off"),
        "toggle": t("toggle")
    }
    return action_map.get(service, service.replace('_', ' '))


async def _control_switch_task(
    ws: WebSocketApp,
    group_id: str,
    message_id: Optional[str],
    service: str,
    entity_ids: List[str]
):
    """Async task: control switch(es) with specified service"""
    try:
        client = HomeAssistantClient()
        try:
            if not entity_ids:
                service_name = service.replace('_', '')
                response_text = t("please_specify_entity_id", service_name=service_name)
            else:
                results = []
                errors = []
                
                for alias_or_id in entity_ids:
                    try:
                        # Try to find entity ID by alias using cache
                        from meteion.utils.entity_cache import find_entity_by_alias
                        entity_id = find_entity_by_alias(alias_or_id)
                        if not entity_id:
                            errors.append((alias_or_id, "Entity not found"))
                            logger.warning(f"Entity not found for alias/ID: {alias_or_id}")
                            continue
                        
                        # Extract domain from entity_id (e.g., 'light.xxx' -> 'light')
                        domain = _extract_domain(entity_id)
                        result = await client.call_service(domain, service, entity_id=entity_id)
                        results.append((alias_or_id, True, result))
                    except Exception as e:
                        errors.append((alias_or_id, str(e)))
                        logger.error(f"Error calling {service} for {alias_or_id}: {e}")
                
                # Build response after processing all entities
                action = _get_service_action(service)
                
                if errors and not results:
                    error_msgs = [f"{eid}: {err}" for eid, err in errors]
                    response_text = t("action_failed", action=action, errors="\n".join(error_msgs))
                elif errors:
                    success_count = len(results)
                    error_msgs = [f"{eid}: {err}" for eid, err in errors]
                    response_text = t("success_action_count", action=action, count=success_count, errors="\n".join(error_msgs))
                else:
                    entity_list = ", ".join(entity_ids)
                    response_text = t("success_action", action=action, entity_list=entity_list)
                        
        except Exception as e:
            logger.error(f"Error in {service} task: {e}", exc_info=True)
            action = _get_service_action(service)
            response_text = t("error_executing_action", action=action, error=str(e))
        finally:
            await client.close()
        
        _send_response(ws, group_id, message_id, response_text)
    except Exception as e:
        logger.error(f"Error in control_switch_task: {e}", exc_info=True)
        _send_response(ws, group_id, message_id, t("error_processing_command", error=str(e)))


def turn_on_handler(ws: WebSocketApp, message: dict):
    """Handle /turnon command"""
    group_id = message["group_id"]
    message_id = message.get("message_id")
    raw_message = message.get("raw_message", "").strip()
    
    entity_ids = _parse_entity_ids(raw_message, "/turnon ")
    task = _control_switch_task(ws, group_id, message_id, "turn_on", entity_ids)
    thread = threading.Thread(target=_run_async_task, args=(task,), daemon=True)
    thread.start()


def turn_off_handler(ws: WebSocketApp, message: dict):
    """Handle /turnoff command"""
    group_id = message["group_id"]
    message_id = message.get("message_id")
    raw_message = message.get("raw_message", "").strip()
    
    entity_ids = _parse_entity_ids(raw_message, "/turnoff ")
    task = _control_switch_task(ws, group_id, message_id, "turn_off", entity_ids)
    thread = threading.Thread(target=_run_async_task, args=(task,), daemon=True)
    thread.start()


def toggle_handler(ws: WebSocketApp, message: dict):
    """Handle /toggle command"""
    group_id = message["group_id"]
    message_id = message.get("message_id")
    raw_message = message.get("raw_message", "").strip()
    
    entity_ids = _parse_entity_ids(raw_message, "/toggle ")
    task = _control_switch_task(ws, group_id, message_id, "toggle", entity_ids)
    thread = threading.Thread(target=_run_async_task, args=(task,), daemon=True)
    thread.start()


async def _info_task(ws: WebSocketApp, group_id: str, message_id: Optional[str]):
    """Async task: get live context information"""
    try:
        client = HomeAssistantClient()
        try:
            result = await client.get_live_context()
            
            response_text = ""
            if isinstance(result, dict):
                response = result.get("response", {})
                
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
                response_text = str(result) if result else t("unable_to_get_context")
                
        except Exception as e:
            logger.error(f"Error getting live context: {e}", exc_info=True)
            response_text = t("error_getting_context", error=str(e))
        finally:
            await client.close()
        
        _send_response(ws, group_id, message_id, response_text)
    except Exception as e:
        logger.error(f"Error in info_task: {e}", exc_info=True)
        _send_response(ws, group_id, message_id, t("error_processing_command", error=str(e)))


def info_handler(ws: WebSocketApp, message: dict):
    """Handle /info command"""
    group_id = message["group_id"]
    message_id = message.get("message_id")
    
    task = _info_task(ws, group_id, message_id)
    thread = threading.Thread(target=_run_async_task, args=(task,), daemon=True)
    thread.start()


def on_error(ws, error):
    logger.error(error)


def on_open(ws):
    """WebSocket connection opened"""
    set_ws_connection(ws)
    logger.info("WebSocket connection established")
    
    # Load entity cache in background
    def load_cache():
        from meteion.utils.entity_cache import load_entity_cache
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(load_entity_cache())
        finally:
            loop.close()
    
    cache_thread = threading.Thread(target=load_cache, daemon=True)
    cache_thread.start()


def on_message(ws, message):
    message = json.loads(message)
    post_type = message.get("post_type", None)

    if post_type != "message" or message.get("message_type") != "group":
        return

    raw_message = message.get("raw_message", "").strip()
    
    if raw_message.startswith("/echo "):
        echo_handler(ws, message)
    elif raw_message == "/clear":
        clear_handler(ws, message)
    elif raw_message.startswith("/turnon "):
        turn_on_handler(ws, message)
    elif raw_message.startswith("/turnoff "):
        turn_off_handler(ws, message)
    elif raw_message.startswith("/toggle "):
        toggle_handler(ws, message)
    elif raw_message == "/info":
        info_handler(ws, message)
    elif raw_message:
        conversation_handler(ws, message)

