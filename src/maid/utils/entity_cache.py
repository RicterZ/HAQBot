"""Entity cache for Home Assistant entities"""
from typing import Optional, Dict, Any, List, Tuple
from threading import Lock

from maid.utils.logger import logger
from maid.utils.i18n import t

# Global cache
_entity_cache: Optional[List[Dict[str, Any]]] = None
_device_cache: Optional[List[Dict[str, Any]]] = None
_area_cache: Optional[Dict[str, Dict[str, Any]]] = None
_entity_areas_cache: Optional[Dict[str, str]] = None
_cache_lock = Lock()


async def load_entity_cache() -> bool:
    """Load entity, device and area cache from Home Assistant
    
    Returns:
        True if cache loaded successfully, False otherwise
    """
    global _entity_cache, _device_cache, _area_cache, _entity_areas_cache
    
    try:
        # Import here to avoid circular dependency
        from maid.clients.homeassistant import HomeAssistantClient
        
        client = HomeAssistantClient()
        try:
            logger.info("Loading entity, device and area cache from Home Assistant...")
            states = await client.get_states()
            devices = _extract_devices_from_states(states)
            areas = {}
            
            entity_areas = {}
            try:
                entity_areas = await client.get_entity_areas()
                logger.info(f"Loaded area information for {len(entity_areas)} entities")
                if entity_areas:
                    entities_with_area = sum(1 for area in entity_areas.values() if area)
                    logger.info(f"Entity areas: {entities_with_area}/{len(entity_areas)} entities have area")
            except Exception as area_error:
                logger.warning(f"Failed to get entity areas: {area_error}")
                logger.warning("Entity area information is required for area grouping. Devices will be shown as ungrouped.")
            
            with _cache_lock:
                _entity_cache = states
                _device_cache = devices
                _area_cache = areas
                _entity_areas_cache = entity_areas
            
            logger.info(f"Entity cache loaded: {len(states)} entities, {len(devices)} devices, {len(areas)} areas")
            
            return True
        finally:
            await client.close()
    except Exception as e:
        logger.error(f"Failed to load entity cache: {e}", exc_info=True)
        return False


def _extract_devices_from_states(states: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Extract device information from entity states
    
    Args:
        states: List of entity state dictionaries
    
    Returns:
        List of device dictionaries
    """
    devices_dict = {}
    
    for state in states:
        entity_id = state.get("entity_id", "")
        attributes = state.get("attributes", {})
        
        device_id = attributes.get("device_id")
        if not device_id:
            device_id = f"virtual_{entity_id}"
        
        if device_id not in devices_dict:
            area_id = attributes.get("area_id")
            device_name = attributes.get("device_name") or attributes.get("friendly_name") or entity_id.split(".")[-1]
            
            devices_dict[device_id] = {
                "id": device_id,
                "name": device_name,
                "area_id": area_id,
                "entities": []
            }
        
        devices_dict[device_id]["entities"].append(entity_id)
    
    return list(devices_dict.values())


def get_entity_cache() -> Optional[List[Dict[str, Any]]]:
    """Get cached entity list
    
    Returns:
        Cached entity list or None if not initialized
    """
    with _cache_lock:
        return _entity_cache


def get_device_cache() -> Optional[List[Dict[str, Any]]]:
    """Get cached device list
    
    Returns:
        Cached device list or None if not initialized
    """
    with _cache_lock:
        return _device_cache


def get_area_cache() -> Optional[Dict[str, Dict[str, Any]]]:
    """Get cached area list
    
    Returns:
        Cached area dictionary or None if not initialized
    """
    with _cache_lock:
        return _area_cache


def get_entity_areas_cache() -> Optional[Dict[str, str]]:
    """Get cached entity areas (entity_id -> area_name)
    
    Returns:
        Cached entity areas dictionary or None if not initialized
"""
    with _cache_lock:
        return _entity_areas_cache


def get_devices_by_domain(domain: str) -> Dict[Optional[str], List[Dict[str, Any]]]:
    """Get devices filtered by domain, grouped by area
    
    Args:
        domain: Entity domain (e.g., 'light', 'switch')
    
    Returns:
        Dictionary mapping area_id to list of devices
    """
    cache = get_entity_cache()
    device_cache = get_device_cache()
    entity_areas = get_entity_areas_cache() or {}
    if not cache:
        return {}
    
    devices_by_area = {}
    device_entities_map = {}
    device_name_map = {}
    device_area_map = {}
    
    if device_cache:
        for device in device_cache:
            device_id = device.get("id")
            if device_id:
                device_name_map[device_id] = device.get("name", "")
                device_area_map[device_id] = device.get("area_id")
    
    for state in cache:
        entity_id = state.get("entity_id", "")
        if not entity_id.startswith(f"{domain}."):
            continue
        
        attributes = state.get("attributes", {})
        device_id = attributes.get("device_id")
        entity_state = state.get("state", "")
        
        if not device_id:
            device_id = f"virtual_{entity_id}"
        
        if device_id not in device_entities_map:
            area_name = entity_areas.get(entity_id, "")
            area_id = None
            if area_name:
                area_cache = get_area_cache() or {}
                for cached_area_id, area_info in area_cache.items():
                    if isinstance(area_info, dict) and area_info.get("name") == area_name:
                        area_id = cached_area_id
                        break
                if not area_id:
                    area_id = area_name
            
            if not area_id:
                area_id = device_area_map.get(device_id)
            if not area_id:
                area_id = attributes.get("area_id") or attributes.get("area") or attributes.get("room")
            
            device_name = (
                device_name_map.get(device_id) or
                attributes.get("device_name") or
                attributes.get("friendly_name") or
                entity_id.split(".")[-1]
            )
            device_entities_map[device_id] = {
                "device_id": device_id,
                "device_name": device_name,
                "area_id": area_id,
                "entities": [],
                "states": []
            }
        
        device_entities_map[device_id]["entities"].append(entity_id)
        device_entities_map[device_id]["states"].append(entity_state)
    
    for device_id, device_info in device_entities_map.items():
        area_id = device_info["area_id"]
        area_key = str(area_id) if area_id is not None else None
        
        if area_key not in devices_by_area:
            devices_by_area[area_key] = []
        
        on_count = sum(1 for s in device_info["states"] if s.lower() == "on")
        total_count = len(device_info["states"])
        if total_count > 1:
            state_summary = f"{on_count}/{total_count}"
        else:
            state = device_info["states"][0] if device_info["states"] else "unknown"
            state_lower = state.lower()
            if state_lower == "on":
                state_summary = t("state_on")
            elif state_lower == "off":
                state_summary = t("state_off")
            else:
                state_summary = t("state_unknown")
        
        devices_by_area[area_key].append({
            "device_name": device_info["device_name"],
            "state_summary": state_summary,
            "entity_count": total_count
        })
    
    return devices_by_area


def find_entity_by_name(name: str) -> Tuple[Optional[str], List[str]]:
    """Find entity ID by friendly_name or entity_id using cached entities
    
    Args:
        name: Friendly name or entity ID to search for
    
    Returns:
        Tuple of (first matching entity_id, list of all matching entity_ids)
    """
    if '.' in name:
        logger.debug(f"Treating '{name}' as entity_id")
        return name, [name]
    
    cache = get_entity_cache()
    if not cache:
        logger.warning("Entity cache not initialized, cannot find entity by name")
        return None, []
    
    name_lower = name.lower()
    matches = []
    
    for state in cache:
        entity_id = state.get("entity_id", "")
        attributes = state.get("attributes", {})
        friendly_name = attributes.get("friendly_name", "")
        
        if friendly_name and friendly_name.lower() == name_lower:
            logger.debug(f"Found entity {entity_id} by friendly_name: {friendly_name}")
            matches.append(entity_id)
            continue
        
        if entity_id.lower().endswith(f".{name_lower}"):
            logger.debug(f"Found entity {entity_id} by entity_id pattern")
            matches.append(entity_id)
    
    if not matches:
        logger.debug(f"No entity found for name: {name}")
        return None, []
    
    logger.debug(f"Found {len(matches)} match(es) for name '{name}': {matches}")
    return matches[0], matches

