import json
import os
import asyncio
import threading
from typing import Optional, List, Dict

from websocket import WebSocketApp

from maid.utils import CommandEncoder
from maid.utils.logger import logger
from maid.utils.i18n import t
from maid.utils.response import send_response, run_async_task
from maid.models.message import Command, CommandType, TextMessage
from maid.handlers.conversation import conversation_handler, clear_conversation_context
from maid.bot.connection import set_ws_connection
from maid.clients.homeassistant import HomeAssistantClient


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
    send_response(ws, group_id, message_id, response_text)


def _get_allowed_senders() -> Optional[List[str]]:
    """Get list of allowed sender QQ numbers from environment variable
    
    Returns:
        List of allowed QQ numbers, or None if all users are allowed
    """
    allowed = os.getenv("ALLOWED_SENDERS", "").strip()
    if not allowed:
        return None
    
    # Support comma or space separated QQ numbers
    qq_list = [qq.strip() for qq in allowed.replace(",", " ").split() if qq.strip()]
    return qq_list if qq_list else None


def _is_sender_allowed(message: dict) -> bool:
    """Check if the sender is allowed to control devices
    
    Args:
        message: Message dictionary from WebSocket
    
    Returns:
        True if sender is allowed, False otherwise
    """
    allowed_senders = _get_allowed_senders()
    
    if allowed_senders is None:
        return True
    
    # Try multiple possible field names for user ID
    user_id = message.get("user_id") or message.get("sender_id")
    
    if not user_id:
        logger.warning(f"Cannot determine sender QQ number from message. Available keys: {list(message.keys())}")
        return False
    
    user_id_str = str(user_id)
    return user_id_str in allowed_senders


def _parse_entity_ids(raw_message: str, command_prefix: str) -> List[str]:
    """Parse entity IDs from command message, supporting quoted names with spaces
    
    Examples:
        /turnon light1 light2 -> ['light1', 'light2']
        /turnon "Apple TV" light1 -> ['Apple TV', 'light1']
        /turnon 'Living Room' -> ['Living Room']
    """
    if not raw_message.startswith(command_prefix):
        return []
    
    args = raw_message[len(command_prefix):].strip()
    if not args:
        return []
    
    entity_ids = []
    current = ""
    in_quotes = False
    quote_char = None
    
    i = 0
    while i < len(args):
        char = args[i]
        
        if char in ['"', "'"]:
            if not in_quotes:
                in_quotes = True
                quote_char = char
            elif char == quote_char:
                in_quotes = False
                quote_char = None
                if current.strip():
                    entity_ids.append(current.strip())
                    current = ""
            else:
                current += char
        elif char == ' ' and not in_quotes:
            if current.strip():
                entity_ids.append(current.strip())
                current = ""
        else:
            current += char
        
        i += 1
    
    if current.strip():
        entity_ids.append(current.strip())
    
    return [eid for eid in entity_ids if eid]


def _extract_domain(entity_id: str) -> str:
    """Extract domain from entity ID (e.g., 'light.xxx' -> 'light')"""
    if '.' in entity_id:
        return entity_id.split('.')[0]
    return "switch"


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
                        from maid.utils.entity_cache import find_entity_by_alias
                        entity_id, all_matches = find_entity_by_alias(alias_or_id)
                        if not entity_id:
                            errors.append((alias_or_id, t("entity_not_found")))
                            logger.warning(f"Entity not found for alias/ID: {alias_or_id}")
                            continue
                        
                        warning_msg = ""
                        if len(all_matches) > 1:
                            warning_msg = t("multiple_entities_found", alias=alias_or_id, count=len(all_matches), first=entity_id)
                            logger.warning(f"Multiple entities found for alias '{alias_or_id}': {all_matches}, using first: {entity_id}")
                        
                        domain = _extract_domain(entity_id)
                        result = await client.call_service(domain, service, entity_id=entity_id)
                        results.append({
                            "alias": alias_or_id,
                            "success": True,
                            "result": result,
                            "warning": warning_msg
                        })
                    except Exception as e:
                        errors.append((alias_or_id, str(e)))
                        logger.error(f"Error calling {service} for {alias_or_id}: {e}")
                
                action = _get_service_action(service)
                warnings = [r["warning"] for r in results if r.get("warning")]
                
                if errors and not results:
                    error_msgs = [f"{eid}: {err}" for eid, err in errors]
                    response_text = t("action_failed", action=action, errors="\n".join(error_msgs))
                elif errors:
                    success_count = len(results)
                    error_msgs = [f"{eid}: {err}" for eid, err in errors]
                    response_text = t("success_action_count", action=action, count=success_count, errors="\n".join(error_msgs))
                    if warnings:
                        response_text += "\n\n" + "\n".join(warnings)
                else:
                    entity_list = ", ".join([r["alias"] for r in results])
                    response_text = t("success_action", action=action, entity_list=entity_list)
                    if warnings:
                        response_text += "\n\n" + "\n".join(warnings)
                        
        except Exception as e:
            logger.error(f"Error in {service} task: {e}", exc_info=True)
            action = _get_service_action(service)
            response_text = t("error_executing_action", action=action, error=str(e))
        finally:
            await client.close()
        
        send_response(ws, group_id, message_id, response_text)
    except Exception as e:
        logger.error(f"Error in control_switch_task: {e}", exc_info=True)
        send_response(ws, group_id, message_id, t("error_processing_command", error=str(e)))


def turn_on_handler(ws: WebSocketApp, message: dict):
    """Handle /turnon command"""
    if not _is_sender_allowed(message):
        return
    
    group_id = message["group_id"]
    message_id = message.get("message_id")
    raw_message = message.get("raw_message", "").strip()
    
    entity_ids = _parse_entity_ids(raw_message, "/turnon ")
    task = _control_switch_task(ws, group_id, message_id, "turn_on", entity_ids)
    thread = threading.Thread(target=run_async_task, args=(task,), daemon=True)
    thread.start()


def turn_off_handler(ws: WebSocketApp, message: dict):
    """Handle /turnoff command"""
    if not _is_sender_allowed(message):
        return
    
    group_id = message["group_id"]
    message_id = message.get("message_id")
    raw_message = message.get("raw_message", "").strip()
    
    entity_ids = _parse_entity_ids(raw_message, "/turnoff ")
    task = _control_switch_task(ws, group_id, message_id, "turn_off", entity_ids)
    thread = threading.Thread(target=run_async_task, args=(task,), daemon=True)
    thread.start()


def toggle_handler(ws: WebSocketApp, message: dict):
    """Handle /toggle command"""
    if not _is_sender_allowed(message):
        return
    
    group_id = message["group_id"]
    message_id = message.get("message_id")
    raw_message = message.get("raw_message", "").strip()
    
    entity_ids = _parse_entity_ids(raw_message, "/toggle ")
    task = _control_switch_task(ws, group_id, message_id, "toggle", entity_ids)
    thread = threading.Thread(target=run_async_task, args=(task,), daemon=True)
    thread.start()


async def _info_task(ws: WebSocketApp, group_id: str, message_id: Optional[str]):
    """Async task: get home context information - only important status"""
    try:
        client = HomeAssistantClient()
        try:
            context = await client.get_context_info()
            
            lines = []
            lines.append(t("context_info_header"))
            
            if context["lights_on"]:
                lines.append(f"\n{t('lights_on')}:")
                for light in context["lights_on"]:
                    brightness = light.get("brightness")
                    if brightness:
                        lines.append(f"  •{light['friendly_name']} ({brightness}%)")
                    else:
                        lines.append(f"  •{light['friendly_name']}")
            
            if context["climate"]:
                lines.append(f"\n{t('climate_devices')}:")
                for climate in context["climate"]:
                    parts = []
                    if climate.get("current_temp"):
                        parts.append(f"{t('current_temp')}: {climate['current_temp']}°C")
                    if climate.get("target_temp"):
                        parts.append(f"{t('target_temp')}: {climate['target_temp']}°C")
                    if climate.get("hvac_mode"):
                        parts.append(f"{t('mode')}: {climate['hvac_mode']}")
                    if climate.get("fan_mode"):
                        parts.append(f"{t('fan')}: {climate['fan_mode']}")
                    
                    status = " - ".join(parts) if parts else climate.get("hvac_mode", "")
                    lines.append(f"  •{climate['friendly_name']}: {status}")
            
            if context["temperature_sensors"]:
                lines.append(f"\n{t('temperature')}:")
                for temp in context["temperature_sensors"][:5]:
                    lines.append(f"  •{temp['friendly_name']}: {temp['value']} {temp['unit']}")
            
            if context["humidity_sensors"]:
                lines.append(f"\n{t('humidity')}:")
                for humidity in context["humidity_sensors"][:5]:
                    lines.append(f"  •{humidity['friendly_name']}: {humidity['value']} {humidity['unit']}")
            
            if context["important_binary_sensors"]:
                lines.append(f"\n{t('important_status')}:")
                for sensor in context["important_binary_sensors"]:
                    device_class = sensor.get("device_class", "")
                    icon_map = {
                        "door": "🚪",
                        "window": "🪟",
                        "motion": "👁️",
                        "occupancy": "🏠",
                        "smoke": "🔥",
                        "gas": "⚠️",
                        "moisture": "💧"
                    }
                    icon = icon_map.get(device_class, "•")
                    lines.append(f"  {icon} {sensor['friendly_name']}")
            
            if len(lines) == 1:
                lines.append(f"\n{t('no_status_info')}")
            
            response_text = "\n".join(lines)
                
        except Exception as e:
            logger.error(f"Error getting context: {e}", exc_info=True)
            response_text = t("error_getting_context", error=str(e))
        finally:
            await client.close()
        
        send_response(ws, group_id, message_id, response_text)
    except Exception as e:
        logger.error(f"Error in info_task: {e}", exc_info=True)
        send_response(ws, group_id, message_id, t("error_processing_command", error=str(e)))


def info_handler(ws: WebSocketApp, message: dict):
    """Handle /info command - uses direct API calls"""
    group_id = message["group_id"]
    message_id = message.get("message_id")
    
    task = _info_task(ws, group_id, message_id)
    thread = threading.Thread(target=run_async_task, args=(task,), daemon=True)
    thread.start()


async def _list_domain_task(
    ws: WebSocketApp,
    group_id: str,
    message_id: Optional[str],
    domain: str
):
    """Async task: list devices by domain, grouped by area"""
    try:
        from maid.utils.entity_cache import get_devices_by_domain, get_area_cache
        
        devices_by_area = get_devices_by_domain(domain)
        area_cache = get_area_cache() or {}
        
        if not devices_by_area:
            response_text = t("no_devices_found", domain=domain)
        else:
            lines = []
            lines.append(t("devices_list_header", domain=domain))
            
            sorted_areas = sorted(devices_by_area.items(), key=lambda x: (x[0] is None, x[0] or ""))
            
            for area_id, devices in sorted_areas:
                if area_id:
                    # area_id might be area_name (from template API) or actual area_id
                    # Try to get area name from cache first
                    area_info = area_cache.get(str(area_id))
                    if isinstance(area_info, dict):
                        area_name = area_info.get("name") or area_info.get("area_name") or str(area_id)
                    else:
                        # If not found in cache, area_id might already be area_name
                        area_name = str(area_id)
                    lines.append(f"\n{t('area')}: {area_name}")
                else:
                    lines.append(f"\n{t('ungrouped')}")
                
                for device in devices:
                    device_name = device["device_name"]
                    state_summary = device["state_summary"]
                    lines.append(f"  •{device_name} - {state_summary}")
            
            response_text = "\n".join(lines)
        
        send_response(ws, group_id, message_id, response_text)
    except Exception as e:
        logger.error(f"Error in list_domain_task: {e}", exc_info=True)
        send_response(ws, group_id, message_id, t("error_processing_command", error=str(e)))


def light_handler(ws: WebSocketApp, message: dict):
    """Handle /light command"""
    group_id = message["group_id"]
    message_id = message.get("message_id")
    
    task = _list_domain_task(ws, group_id, message_id, "light")
    thread = threading.Thread(target=run_async_task, args=(task,), daemon=True)
    thread.start()


def switch_handler(ws: WebSocketApp, message: dict):
    """Handle /switch command"""
    group_id = message["group_id"]
    message_id = message.get("message_id")
    
    task = _list_domain_task(ws, group_id, message_id, "switch")
    thread = threading.Thread(target=run_async_task, args=(task,), daemon=True)
    thread.start()


def _get_commands_list() -> List[Dict[str, str]]:
    """Get list of all supported commands with descriptions
    
    Returns:
        List of command dictionaries with 'command', 'description', and 'emoji' keys
    """
    return [
        {
            "command": "/help",
            "description": t("help_command_description"),
            "emoji": "📋"
        },
        {
            "command": "/info",
            "description": t("info_command_description"),
            "emoji": "🏠"
        },
        {
            "command": "/turnon <entity_id> [<entity_id2> ...]",
            "description": t("turnon_command_description"),
            "emoji": "💡"
        },
        {
            "command": "/turnoff <entity_id> [<entity_id2> ...]",
            "description": t("turnoff_command_description"),
            "emoji": "🔌"
        },
        {
            "command": "/toggle <entity_id> [<entity_id2> ...]",
            "description": t("toggle_command_description"),
            "emoji": "🔄"
        },
        {
            "command": "/light",
            "description": t("light_command_description"),
            "emoji": "💡"
        },
        {
            "command": "/switch",
            "description": t("switch_command_description"),
            "emoji": "🔌"
        },
        {
            "command": "/search <query>",
            "description": t("search_command_description"),
            "emoji": "🔍"
        },
        {
            "command": "/clear",
            "description": t("clear_command_description"),
            "emoji": "🗑️"
        },
        {
            "command": "/echo <text>",
            "description": t("echo_command_description"),
            "emoji": "📢"
        },
    ]


def _search_entities(query: str, limit: int = 20) -> List[Dict[str, str]]:
    """Search entities by fuzzy matching on entity_id, friendly_name, and aliases
    
    Args:
        query: Search query string
        limit: Maximum number of results to return
    
    Returns:
        List of matching entities with entity_id and friendly_name
    """
    from maid.utils.entity_cache import get_entity_cache
    
    cache = get_entity_cache()
    if not cache:
        return []
    
    query_lower = query.lower()
    matches = []
    
    for state in cache:
        entity_id = state.get("entity_id", "")
        attributes = state.get("attributes", {})
        friendly_name = attributes.get("friendly_name", "") or entity_id
        
        # Check if query matches entity_id (case-insensitive, partial match)
        if query_lower in entity_id.lower():
            matches.append({
                "entity_id": entity_id,
                "friendly_name": friendly_name
            })
            continue
        
        # Check if query matches friendly_name (case-insensitive, partial match)
        if friendly_name and query_lower in friendly_name.lower():
            matches.append({
                "entity_id": entity_id,
                "friendly_name": friendly_name
            })
            continue
        
        # Check if query matches any alias
        for attr_key, attr_value in attributes.items():
            if attr_key in ["aliases", "alias", "device_aliases"]:
                if isinstance(attr_value, list):
                    for alias in attr_value:
                        if isinstance(alias, str) and query_lower in alias.lower():
                            matches.append({
                                "entity_id": entity_id,
                                "friendly_name": friendly_name
                            })
                            break
                elif isinstance(attr_value, str) and query_lower in attr_value.lower():
                    matches.append({
                        "entity_id": entity_id,
                        "friendly_name": friendly_name
                    })
                    break
        
        if len(matches) >= limit:
            break
    
    return matches[:limit]


def search_handler(ws: WebSocketApp, message: dict):
    """Handle /search command"""
    group_id = message["group_id"]
    message_id = message.get("message_id")
    raw_message = message.get("raw_message", "").strip()
    
    # Extract search query
    if not raw_message.startswith("/search "):
        response_text = t("search_usage")
        send_response(ws, group_id, message_id, response_text)
        return
    
    query = raw_message[8:].strip()  # Remove "/search "
    if not query:
        response_text = t("search_usage")
        send_response(ws, group_id, message_id, response_text)
        return
    
    # Search entities
    matches = _search_entities(query, limit=20)
    
    if not matches:
        response_text = t("search_no_results", query=query)
    else:
        lines = []
        lines.append(t("search_results_header", query=query, count=len(matches)))
        for match in matches:
            lines.append(f"  • {match['friendly_name']} ({match['entity_id']})")
        
        if len(matches) == 20:
            lines.append(f"\n{t('search_results_truncated')}")
        
        response_text = "\n".join(lines)
    
    send_response(ws, group_id, message_id, response_text)


def help_handler(ws: WebSocketApp, message: dict):
    """Handle /help command"""
    group_id = message["group_id"]
    message_id = message.get("message_id")
    
    commands = _get_commands_list()
    
    lines = []
    lines.append(t("help_header"))
    
    for cmd_info in commands:
        emoji = cmd_info.get("emoji", "•")
        lines.append(f"{emoji} {cmd_info['command']} - {cmd_info['description']}")
    
    response_text = "\n".join(lines)
    send_response(ws, group_id, message_id, response_text)


def on_error(ws, error):
    logger.error(error)


def on_open(ws):
    """WebSocket connection opened"""
    set_ws_connection(ws)
    logger.info("WebSocket connection established")
    
    def load_cache():
        from maid.utils.entity_cache import load_entity_cache
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
    elif raw_message == "/light":
        light_handler(ws, message)
    elif raw_message == "/switch":
        switch_handler(ws, message)
    elif raw_message.startswith("/search "):
        search_handler(ws, message)
    elif raw_message == "/help":
        help_handler(ws, message)
    elif raw_message:
        if not _is_sender_allowed(message):
            return
        conversation_handler(ws, message)

