import json
import asyncio
import threading
from typing import Optional, List, Dict

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
                        entity_id, all_matches = find_entity_by_alias(alias_or_id)
                        if not entity_id:
                            errors.append((alias_or_id, t("entity_not_found")))
                            logger.warning(f"Entity not found for alias/ID: {alias_or_id}")
                            continue
                        
                        # Warn if multiple matches found
                        warning_msg = ""
                        if len(all_matches) > 1:
                            warning_msg = t("multiple_entities_found", alias=alias_or_id, count=len(all_matches), first=entity_id)
                            logger.warning(f"Multiple entities found for alias '{alias_or_id}': {all_matches}, using first: {entity_id}")
                        
                        # Extract domain from entity_id (e.g., 'light.xxx' -> 'light')
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
                
                # Build response after processing all entities
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
    """Async task: get live context information using direct API calls"""
    try:
        client = HomeAssistantClient()
        try:
            # Use direct API calls
            context = await client.get_context_info()
            
            lines = []
            lines.append(t("context_info_header"))
            lines.append(f"\n{t('total_entities')}: {context['total_entities']}")
            
            # Show summary by domain
            if context["sensors"]:
                lines.append(f"\n{t('sensors')}: {len(context['sensors'])}")
                # Show first few important sensors
                important_sensors = [s for s in context["sensors"][:5]]
                for sensor in important_sensors:
                    unit = sensor.get("unit", "")
                    state_str = f"{sensor['state']} {unit}".strip()
                    lines.append(f"  • {sensor['friendly_name']}: {state_str}")
                if len(context["sensors"]) > 5:
                    lines.append(t("more_sensors", count=len(context['sensors']) - 5))
            
            if context["switches"]:
                on_count = sum(1 for s in context["switches"] if s["state"] == "on")
                lines.append(f"\n{t('switches')}: {len(context['switches'])} ({t('on_count')}: {on_count})")
            
            if context["lights"]:
                on_count = sum(1 for l in context["lights"] if l["state"] == "on")
                lines.append(f"\n{t('lights')}: {len(context['lights'])} ({t('on_count')}: {on_count})")
            
            if context["climate"]:
                lines.append(f"\n{t('climate')}: {len(context['climate'])}")
                for climate in context["climate"][:3]:
                    lines.append(f"  • {climate['friendly_name']}: {climate['state']}")
            
            if context["binary_sensors"]:
                on_count = sum(1 for bs in context["binary_sensors"] if bs["state"] == "on")
                lines.append(f"\n{t('binary_sensors')}: {len(context['binary_sensors'])} ({t('on_count')}: {on_count})")
            
            response_text = "\n".join(lines)
                
        except Exception as e:
            logger.error(f"Error getting context: {e}", exc_info=True)
            response_text = t("error_getting_context", error=str(e))
        finally:
            await client.close()
        
        _send_response(ws, group_id, message_id, response_text)
    except Exception as e:
        logger.error(f"Error in info_task: {e}", exc_info=True)
        _send_response(ws, group_id, message_id, t("error_processing_command", error=str(e)))


def info_handler(ws: WebSocketApp, message: dict):
    """Handle /info command - uses direct API calls"""
    group_id = message["group_id"]
    message_id = message.get("message_id")
    
    task = _info_task(ws, group_id, message_id)
    thread = threading.Thread(target=_run_async_task, args=(task,), daemon=True)
    thread.start()


async def _list_domain_task(
    ws: WebSocketApp,
    group_id: str,
    message_id: Optional[str],
    domain: str
):
    """Async task: list entities by domain, grouped by area"""
    try:
        from meteion.utils.entity_cache import get_entities_by_domain, get_area_cache
        
        entities_by_area = get_entities_by_domain(domain)
        area_cache = get_area_cache() or {}
        
        if not entities_by_area:
            response_text = t("no_entities_found", domain=domain)
        else:
            lines = []
            lines.append(t("entities_list_header", domain=domain))
            
            # Sort areas: None (ungrouped) last
            sorted_areas = sorted(
                entities_by_area.items(),
                key=lambda x: (x[0] is None, x[0] or "")
            )
            
            for area_id, entities in sorted_areas:
                if area_id:
                    area_name = area_cache.get(area_id, {}).get("name", area_id)
                    lines.append(f"\n{t('area')}: {area_name}")
                else:
                    lines.append(f"\n{t('ungrouped')}")
                
                for entity in entities:
                    entity_id = entity["entity_id"]
                    friendly_name = entity["friendly_name"]
                    state = entity["state"]
                    lines.append(f"  • {friendly_name} ({entity_id}) - {state}")
            
            response_text = "\n".join(lines)
        
        _send_response(ws, group_id, message_id, response_text)
    except Exception as e:
        logger.error(f"Error in list_domain_task: {e}", exc_info=True)
        _send_response(ws, group_id, message_id, t("error_processing_command", error=str(e)))


def light_handler(ws: WebSocketApp, message: dict):
    """Handle /light command"""
    group_id = message["group_id"]
    message_id = message.get("message_id")
    
    task = _list_domain_task(ws, group_id, message_id, "light")
    thread = threading.Thread(target=_run_async_task, args=(task,), daemon=True)
    thread.start()


def switch_handler(ws: WebSocketApp, message: dict):
    """Handle /switch command"""
    group_id = message["group_id"]
    message_id = message.get("message_id")
    
    task = _list_domain_task(ws, group_id, message_id, "switch")
    thread = threading.Thread(target=_run_async_task, args=(task,), daemon=True)
    thread.start()


def _get_commands_list() -> List[Dict[str, str]]:
    """Get list of all supported commands with descriptions
    
    Returns:
        List of command dictionaries with 'command' and 'description' keys
    """
    return [
        {
            "command": "/help",
            "description": t("help_command_description")
        },
        {
            "command": "/echo <text>",
            "description": t("echo_command_description")
        },
        {
            "command": "/clear",
            "description": t("clear_command_description")
        },
        {
            "command": "/turnon <entity_id> [<entity_id2> ...]",
            "description": t("turnon_command_description")
        },
        {
            "command": "/turnoff <entity_id> [<entity_id2> ...]",
            "description": t("turnoff_command_description")
        },
        {
            "command": "/toggle <entity_id> [<entity_id2> ...]",
            "description": t("toggle_command_description")
        },
        {
            "command": "/info",
            "description": t("info_command_description")
        },
        {
            "command": "/light",
            "description": t("light_command_description")
        },
        {
            "command": "/switch",
            "description": t("switch_command_description")
        },
    ]


def help_handler(ws: WebSocketApp, message: dict):
    """Handle /help command"""
    group_id = message["group_id"]
    message_id = message.get("message_id")
    
    commands = _get_commands_list()
    
    lines = []
    lines.append(t("help_header"))
    lines.append("")
    
    for cmd_info in commands:
        lines.append(f"{cmd_info['command']}")
        lines.append(f"  {cmd_info['description']}")
        lines.append("")
    
    response_text = "\n".join(lines)
    _send_response(ws, group_id, message_id, response_text)


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
    elif raw_message == "/light":
        light_handler(ws, message)
    elif raw_message == "/switch":
        switch_handler(ws, message)
    elif raw_message == "/help":
        help_handler(ws, message)
    elif raw_message:
        conversation_handler(ws, message)

