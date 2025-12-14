"""Information query command handlers"""
import threading
from typing import Optional, List, Dict

from websocket import WebSocketApp

from maid.clients.homeassistant import HomeAssistantClient
from maid.utils.entity_cache import get_devices_by_domain, get_area_cache, get_entity_areas_cache, get_entity_cache
from maid.utils.logger import logger
from maid.utils.i18n import t
from maid.utils.response import send_response, run_async_task


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
                        lines.append(f"  • {light['friendly_name']} ({brightness}%)")
                    else:
                        lines.append(f"  • {light['friendly_name']}")
            
            if context["climate"]:
                lines.append(f"\n{t('climate_devices')}:")
                for climate in context["climate"]:
                    parts = []
                    current_temp = climate.get("current_temp")
                    if current_temp is not None:
                        try:
                            if float(current_temp) != 0:
                                parts.append(f"{t('current_temp')}: {current_temp}°C")
                        except (ValueError, TypeError):
                            pass
                    
                    target_temp = climate.get("target_temp")
                    if target_temp is not None:
                        try:
                            if float(target_temp) != 0:
                                parts.append(f"{t('target_temp')}: {target_temp}°C")
                        except (ValueError, TypeError):
                            pass
                    
                    if climate.get("hvac_mode"):
                        parts.append(f"{t('mode')}: {climate['hvac_mode']}")
                    if climate.get("fan_mode"):
                        parts.append(f"{t('fan')}: {climate['fan_mode']}")
                    
                    # Don't show humidity if it's 0
                    humidity = climate.get("humidity")
                    if humidity is not None:
                        try:
                            if float(humidity) != 0:
                                parts.append(f"{t('humidity')}: {humidity}%")
                        except (ValueError, TypeError):
                            pass
                    
                    status = " - ".join(parts) if parts else climate.get("hvac_mode", "")
                    lines.append(f"  • {climate['friendly_name']}: {status}")
            
            if context["temperature_sensors"]:
                # Group temperature sensors by area
                entity_areas = get_entity_areas_cache() or {}
                area_cache = get_area_cache() or {}
                temp_by_area = {}
                
                for temp in context["temperature_sensors"]:
                    entity_id = temp.get("entity_id", "")
                    area_name = entity_areas.get(entity_id, "")
                    
                    if not area_name:
                        area_name = t("ungrouped_area")
                    
                    if area_name not in temp_by_area:
                        temp_by_area[area_name] = []
                    temp_by_area[area_name].append(temp)
                
                lines.append(f"\n{t('temperature')}:")
                # Sort areas: ungrouped last
                sorted_areas = sorted(temp_by_area.items(), key=lambda x: (x[0] == t("ungrouped_area"), x[0]))
                
                for area_name, temps in sorted_areas:
                    # For each area, show the first temperature sensor (representative)
                    if len(temps) > 0:
                        temp = temps[0]
                        if area_name == t("ungrouped_area"):
                            lines.append(f"  • {temp['friendly_name']}: {temp['value']} {temp['unit']}")
                        else:
                            lines.append(f"  • {area_name}: {temp['value']} {temp['unit']}")
            
            if context["humidity_sensors"]:
                lines.append(f"\n{t('humidity')}:")
                for humidity in context["humidity_sensors"]:
                    lines.append(f"  • {humidity['friendly_name']}: {humidity['value']} {humidity['unit']}")
            
            if context["air_quality_sensors"]:
                lines.append(f"\n{t('air_quality')}:")
                for aq in context["air_quality_sensors"]:
                    unit = aq.get("unit", "")
                    if unit:
                        lines.append(f"  • {aq['friendly_name']}: {aq['value']} {unit}")
                    else:
                        lines.append(f"  • {aq['friendly_name']}: {aq['value']}")
            
            if context["energy_sensors"]:
                lines.append(f"\n{t('energy_consumption')}:")
                for energy in context["energy_sensors"]:
                    unit = energy.get("unit", "kWh")
                    lines.append(f"  • {energy['friendly_name']}: {energy['value']} {unit}")
            
            if context["weather"]:
                lines.append(f"\n{t('weather')}:")
                for weather in context["weather"]:
                    parts = []
                    if weather.get("condition"):
                        parts.append(weather["condition"])
                    if weather.get("temperature") is not None:
                        parts.append(f"{t('temperature')}: {weather['temperature']}°C")
                    if weather.get("humidity") is not None:
                        parts.append(f"{t('humidity')}: {weather['humidity']}%")
                    status = " - ".join(parts) if parts else weather.get("condition", "")
                    lines.append(f"  • {weather['friendly_name']}: {status}")
            
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


def _search_entities(query: str) -> List[Dict[str, str]]:
    """Search entities by fuzzy matching on entity_id and friendly_name
    
    Args:
        query: Search query string
    
    Returns:
        List of matching entities with entity_id and friendly_name
    """
    cache = get_entity_cache()
    if not cache:
        return []
    
    query_lower = query.lower()
    matches = []
    seen_entities = set()  # Avoid duplicates
    
    for state in cache:
        entity_id = state.get("entity_id", "")
        if entity_id in seen_entities:
            continue
        
        attributes = state.get("attributes", {})
        friendly_name = attributes.get("friendly_name", "") or entity_id
        
        matched = False
        
        # Check if query matches entity_id (case-insensitive, partial match)
        if query_lower in entity_id.lower():
            matches.append({
                "entity_id": entity_id,
                "friendly_name": friendly_name
            })
            seen_entities.add(entity_id)
            matched = True
            continue
        
        # Check if query matches friendly_name (case-insensitive, partial match)
        if not matched and friendly_name and query_lower in friendly_name.lower():
            matches.append({
                "entity_id": entity_id,
                "friendly_name": friendly_name
            })
            seen_entities.add(entity_id)
            matched = True
            continue
    
    return matches


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
    matches = _search_entities(query)
    
    if not matches:
        response_text = t("search_no_results", query=query)
    else:
        lines = []
        lines.append(t("search_results_header", query=query, count=len(matches)))
        for match in matches:
            lines.append(f"  • {match['friendly_name']} ({match['entity_id']})")
        
        response_text = "\n".join(lines)
    
    send_response(ws, group_id, message_id, response_text)

