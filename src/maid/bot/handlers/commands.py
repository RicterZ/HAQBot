"""Device control command handlers"""
import threading
from typing import Optional, List, Tuple

from websocket import WebSocketApp

from maid.clients.homeassistant import HomeAssistantClient
from maid.utils.entity_cache import find_entity_by_name
from maid.utils.logger import logger
from maid.utils.i18n import t
from maid.utils.response import send_response, run_async_task


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
                
                for name_or_id in entity_ids:
                    try:
                        entity_id, all_matches = find_entity_by_name(name_or_id)
                        if not entity_id:
                            errors.append((name_or_id, t("entity_not_found")))
                            logger.warning(f"Entity not found for name/ID: {name_or_id}")
                            continue
                        
                        warning_msg = ""
                        if len(all_matches) > 1:
                            warning_msg = t("multiple_entities_found", name=name_or_id, count=len(all_matches), first=entity_id)
                            logger.warning(f"Multiple entities found for name '{name_or_id}': {all_matches}, using first: {entity_id}")
                        
                        domain = _extract_domain(entity_id)
                        result = await client.call_service(domain, service, entity_id=entity_id)
                        results.append({
                            "name": name_or_id,
                            "success": True,
                            "result": result,
                            "warning": warning_msg
                        })
                    except Exception as e:
                        errors.append((name_or_id, str(e)))
                        logger.error(f"Error calling {service} for {name_or_id}: {e}")
                
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
                    entity_list = ", ".join([r["name"] for r in results])
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
    group_id = message["group_id"]
    message_id = message.get("message_id")
    raw_message = message.get("raw_message", "").strip()
    
    entity_ids = _parse_entity_ids(raw_message, "/turnon ")
    task = _control_switch_task(ws, group_id, message_id, "turn_on", entity_ids)
    thread = threading.Thread(target=run_async_task, args=(task,), daemon=True)
    thread.start()


def turn_off_handler(ws: WebSocketApp, message: dict):
    """Handle /turnoff command"""
    group_id = message["group_id"]
    message_id = message.get("message_id")
    raw_message = message.get("raw_message", "").strip()
    
    entity_ids = _parse_entity_ids(raw_message, "/turnoff ")
    task = _control_switch_task(ws, group_id, message_id, "turn_off", entity_ids)
    thread = threading.Thread(target=run_async_task, args=(task,), daemon=True)
    thread.start()


def toggle_handler(ws: WebSocketApp, message: dict):
    """Handle /toggle command"""
    group_id = message["group_id"]
    message_id = message.get("message_id")
    raw_message = message.get("raw_message", "").strip()
    
    entity_ids = _parse_entity_ids(raw_message, "/toggle ")
    task = _control_switch_task(ws, group_id, message_id, "toggle", entity_ids)
    thread = threading.Thread(target=run_async_task, args=(task,), daemon=True)
    thread.start()


def _parse_climate_command(raw_message: str) -> Tuple[Optional[str], Optional[str], Optional[float]]:
    """Parse climate command arguments, supporting quoted entity names with spaces
    
    Args:
        raw_message: Raw message string starting with "/climate "
    
    Returns:
        Tuple of (entity_id, mode, temperature)
        mode can be: cool, heat, fan_only, off, or None
        temperature is float or None
    
    Examples:
        /climate "Living Room AC" cool 26 -> ("Living Room AC", "cool", 26.0)
        /climate 客厅空调 制冷 26 -> ("客厅空调", "cool", 26.0)
        /climate ac temp 25 -> ("ac", None, 25.0)
    """
    if not raw_message.startswith("/climate "):
        return None, None, None
    
    args = raw_message[9:].strip()  # Remove "/climate "
    if not args:
        return None, None, None
    
    # Mode mapping (Chinese to English)
    mode_map = {
        "制冷": "cool",
        "制热": "heat",
        "通风": "fan_only",
        "关闭": "off",
        "off": "off",
        "cool": "cool",
        "heat": "heat",
        "fan_only": "fan_only",
        "fan": "fan_only"
    }
    
    # Parse entity ID first (supporting quoted names)
    entity_id = None
    remaining_args = []
    current = ""
    in_quotes = False
    quote_char = None
    entity_parsed = False
    
    i = 0
    while i < len(args):
        char = args[i]
        
        if not entity_parsed:
            # Still parsing entity ID
            if char in ['"', "'"]:
                if not in_quotes:
                    in_quotes = True
                    quote_char = char
                elif char == quote_char:
                    in_quotes = False
                    quote_char = None
                    if current.strip():
                        entity_id = current.strip()
                        entity_parsed = True
                        current = ""
                else:
                    current += char
            elif char == ' ' and not in_quotes:
                if current.strip():
                    entity_id = current.strip()
                    entity_parsed = True
                    current = ""
            else:
                current += char
        else:
            # Entity ID parsed, collect remaining arguments
            current += char
        
        i += 1
    
    # Handle case where entity ID is at the end (no quotes, no space after)
    if not entity_parsed and current.strip():
        entity_id = current.strip()
        entity_parsed = True
        current = ""
    
    if not entity_id:
        return None, None, None
    
    # Parse remaining arguments for mode and temperature
    remaining = current.strip() if current else ""
    if remaining:
        remaining_parts = remaining.split()
    else:
        remaining_parts = []
    
    mode = None
    temperature = None
    
    i = 0
    while i < len(remaining_parts):
        arg = remaining_parts[i].lower()
        
        # Check if it's a temperature value (number)
        if arg.replace('.', '').replace('-', '').isdigit():
            try:
                temperature = float(arg)
            except ValueError:
                pass
        # Check if it's "temp" keyword followed by temperature
        elif arg == "temp" and i + 1 < len(remaining_parts):
            try:
                temperature = float(remaining_parts[i + 1])
                i += 1  # Skip next token
            except (ValueError, IndexError):
                pass
        # Check if it's a mode (case-insensitive for English, exact match for Chinese)
        elif arg in mode_map:
            mode = mode_map[arg]
        # Check Chinese mode names (case-sensitive)
        elif remaining_parts[i] in ["制冷", "制热", "通风", "关闭"]:
            mode = mode_map[remaining_parts[i]]
        
        i += 1
    
    return entity_id, mode, temperature


async def _climate_control_task(
    ws: WebSocketApp,
    group_id: str,
    message_id: Optional[str],
    entity_id: str,
    mode: Optional[str],
    temperature: Optional[float]
):
    """Async task: control climate device"""
    try:
        client = HomeAssistantClient()
        try:
            # Find entity by name or ID
            logger.debug(f"Searching for climate entity with name/ID: {entity_id}")
            actual_entity_id, all_matches = find_entity_by_name(entity_id)
            if not actual_entity_id:
                logger.warning(f"Climate entity not found for name/ID: {entity_id}")
                response_text = t("entity_not_found")
                send_response(ws, group_id, message_id, response_text)
                return
            
            logger.info(f"Found climate entity: {actual_entity_id} for name/ID: {entity_id}")
            
            warning_msg = ""
            if len(all_matches) > 1:
                warning_msg = t("multiple_entities_found", name=entity_id, count=len(all_matches), first=actual_entity_id)
                logger.warning(f"Multiple entities found for name '{entity_id}': {all_matches}, using first: {actual_entity_id}")
            
            results = []
            
            # Set mode if specified
            if mode:
                if mode == "off":
                    result = await client.call_service("climate", "turn_off", entity_id=actual_entity_id)
                else:
                    result = await client.call_service("climate", "set_hvac_mode", entity_id=actual_entity_id, hvac_mode=mode)
                results.append(t("climate_mode_set", mode=t(f"mode_{mode}")))
            
            # Set temperature if specified
            if temperature is not None:
                result = await client.call_service("climate", "set_temperature", entity_id=actual_entity_id, temperature=temperature)
                results.append(t("climate_temp_set", temp=temperature))
            
            if not results:
                response_text = t("climate_no_params")
            else:
                response_text = " ".join(results)
                if warning_msg:
                    response_text += f"\n{warning_msg}"
                    
        except Exception as e:
            logger.error(f"Error controlling climate device: {e}", exc_info=True)
            response_text = t("error_processing_command", error=str(e))
        finally:
            await client.close()
        
        send_response(ws, group_id, message_id, response_text)
    except Exception as e:
        logger.error(f"Error in climate_control_task: {e}", exc_info=True)
        send_response(ws, group_id, message_id, t("error_processing_command", error=str(e)))


def climate_handler(ws: WebSocketApp, message: dict):
    """Handle /climate command"""
    group_id = message["group_id"]
    message_id = message.get("message_id")
    raw_message = message.get("raw_message", "").strip()
    
    entity_id, mode, temperature = _parse_climate_command(raw_message)
    
    if not entity_id:
        response_text = t("climate_usage")
        send_response(ws, group_id, message_id, response_text)
        return
    
    task = _climate_control_task(ws, group_id, message_id, entity_id, mode, temperature)
    thread = threading.Thread(target=run_async_task, args=(task,), daemon=True)
    thread.start()


async def _script_task(
    ws: WebSocketApp,
    group_id: str,
    message_id: Optional[str],
    script_id: str
):
    """Async task: execute Home Assistant script"""
    try:
        client = HomeAssistantClient()
        try:
            # Scripts are called via script domain, service name is the script entity_id
            # If script_id doesn't start with "script.", add it
            if not script_id.startswith("script."):
                script_entity_id = f"script.{script_id}"
            else:
                script_entity_id = script_id
            
            result = await client.call_service("script", "turn_on", entity_id=script_entity_id)
            
            response_text = t("script_executed", script_id=script_entity_id)
        except Exception as e:
            logger.error(f"Error executing script {script_id}: {e}", exc_info=True)
            response_text = t("script_execution_failed", script_id=script_id, error=str(e))
        finally:
            await client.close()
        
        send_response(ws, group_id, message_id, response_text)
    except Exception as e:
        logger.error(f"Error in script_task: {e}", exc_info=True)
        send_response(ws, group_id, message_id, t("error_processing_command", error=str(e)))


def script_handler(ws: WebSocketApp, message: dict):
    """Handle /script command"""
    group_id = message["group_id"]
    message_id = message.get("message_id")
    raw_message = message.get("raw_message", "").strip()
    
    # Extract script ID
    if not raw_message.startswith("/script "):
        response_text = t("script_usage")
        send_response(ws, group_id, message_id, response_text)
        return
    
    script_id = raw_message[8:].strip()  # Remove "/script "
    if not script_id:
        response_text = t("script_usage")
        send_response(ws, group_id, message_id, response_text)
        return
    
    task = _script_task(ws, group_id, message_id, script_id)
    thread = threading.Thread(target=run_async_task, args=(task,), daemon=True)
    thread.start()

