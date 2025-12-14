"""Entity cache for Home Assistant entities"""
from typing import Optional, Dict, Any, List, Tuple
from threading import Lock

from maid.utils.logger import logger
from maid.utils.i18n import t

# Global cache
_entity_cache: Optional[List[Dict[str, Any]]] = None
_device_cache: Optional[List[Dict[str, Any]]] = None
_area_cache: Optional[Dict[str, Dict[str, Any]]] = None
_entity_registry_cache: Optional[Dict[str, Dict[str, Any]]] = None
_cache_lock = Lock()
_cache_initialized = False


async def load_entity_cache() -> bool:
    """Load entity, device and area cache from Home Assistant
    
    Returns:
        True if cache loaded successfully, False otherwise
    """
    global _entity_cache, _device_cache, _area_cache, _entity_registry_cache, _cache_initialized
    
    try:
        # Import here to avoid circular dependency
        from maid.clients.homeassistant import HomeAssistantClient
        
        client = HomeAssistantClient()
        try:
            logger.info("Loading entity, device and area cache from Home Assistant...")
            states = await client.get_states()
            
            devices = []
            try:
                devices = await client.get_devices()
            except Exception as dev_error:
                logger.debug(f"Failed to get devices from API, extracting from states: {dev_error}")
                devices = _extract_devices_from_states(states)
            
            areas = {}
            try:
                areas = await client.get_areas()
            except Exception as area_error:
                logger.debug(f"Failed to get areas from API: {area_error}")
            
            entity_registry = {}
            try:
                entity_registry = await client.get_entity_registry()
                logger.info(f"Loaded {len(entity_registry)} entities from registry")
                if entity_registry:
                    entities_with_area = sum(1 for e in entity_registry.values() if e.get("area_id"))
                    logger.info(f"Entity registry: {entities_with_area}/{len(entity_registry)} entities have area_id")
            except Exception as reg_error:
                logger.warning(f"Failed to get entity registry: {reg_error}")
            
            with _cache_lock:
                _entity_cache = states
                _device_cache = devices
                _area_cache = areas
                _entity_registry_cache = entity_registry
                _cache_initialized = True
            
            logger.info(f"Entity cache loaded: {len(states)} entities, {len(devices)} devices, {len(areas)} areas")
            
            # Log device area_id statistics for debugging
            if devices:
                devices_with_area = sum(1 for d in devices if d.get("area_id"))
                logger.info(f"Devices with area_id: {devices_with_area}/{len(devices)}")
            
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


def get_entity_registry_cache() -> Optional[Dict[str, Dict[str, Any]]]:
    """Get cached entity registry
    
    Returns:
        Cached entity registry dictionary or None if not initialized
    """
    with _cache_lock:
        return _entity_registry_cache


def get_devices_by_domain(domain: str) -> Dict[Optional[str], List[Dict[str, Any]]]:
    """Get devices filtered by domain, grouped by area
    
    Args:
        domain: Entity domain (e.g., 'light', 'switch')
    
    Returns:
        Dictionary mapping area_id to list of devices
    """
    cache = get_entity_cache()
    device_cache = get_device_cache()
    entity_registry = get_entity_registry_cache() or {}
    if not cache:
        return {}
    
    devices_by_area = {}
    device_entities_map = {}
    device_name_map = {}
    device_area_map = {}
    
    # Build device name and area_id maps from device_cache
    if device_cache:
        for device in device_cache:
            device_id = device.get("id")
            if device_id:
                device_name_map[device_id] = device.get("name", "")
                # area_id is stored in device object
                # Home Assistant device registry returns area_id directly
                area_id = device.get("area_id")
                device_area_map[device_id] = area_id
                if area_id:
                    logger.debug(f"Device {device_id} ({device.get('name', '')}) has area_id: {area_id}")
                else:
                    logger.debug(f"Device {device_id} ({device.get('name', '')}) has no area_id")
    
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
            # Get area_id from device_cache first, then entity registry, then entity attributes
            area_id = device_area_map.get(device_id)
            if not area_id:
                # Try to get from entity registry (entity registry contains area_id)
                entity_info = entity_registry.get(entity_id)
                if entity_info:
                    area_id = entity_info.get("area_id")
                    if area_id:
                        logger.debug(f"Found area_id {area_id} for entity {entity_id} from entity registry")
                    else:
                        logger.debug(f"Entity {entity_id} in registry but has no area_id")
                else:
                    logger.debug(f"Entity {entity_id} not found in entity registry")
            if not area_id:
                # Try to get from entity attributes (though HA states API usually doesn't include this)
                area_id = attributes.get("area_id")
            
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
            if not area_id:
                logger.debug(f"Device {device_id} ({device_name}) has no area_id")
        
        device_entities_map[device_id]["entities"].append(entity_id)
        device_entities_map[device_id]["states"].append(entity_state)
    
    for device_id, device_info in device_entities_map.items():
        area_id = device_info["area_id"]
        # Normalize area_id to string for consistent lookup
        if area_id is not None:
            area_key = str(area_id)
        else:
            area_key = None
        
        if area_key not in devices_by_area:
            devices_by_area[area_key] = []
        
        on_count = sum(1 for s in device_info["states"] if s.lower() == "on")
        total_count = len(device_info["states"])
        if total_count > 1:
            state_summary = f"{on_count}/{total_count}"
        else:
            state = device_info["states"][0] if device_info["states"] else "unknown"
            # Translate state value
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


def is_cache_initialized() -> bool:
    """Check if cache is initialized"""
    with _cache_lock:
        return _cache_initialized


def get_all_entities() -> List[Dict[str, Any]]:
    """Get all entities with formatted information
    
    Returns:
        List of formatted entity dictionaries
    """
    cache = get_entity_cache()
    if not cache:
        return []
    
    with _cache_lock:
        registry = _entity_registry_cache or {}
    
    entities = []
    for state in cache:
        entity_id = state.get("entity_id", "")
        attributes = state.get("attributes", {})
        friendly_name = attributes.get("friendly_name", "")
        domain = entity_id.split(".")[0] if "." in entity_id else ""
        
        # Try to extract aliases from attributes
        aliases = []
        for attr_key in ["aliases", "alias", "device_aliases"]:
            attr_value = attributes.get(attr_key)
            if attr_value:
                if isinstance(attr_value, list):
                    aliases.extend([str(a) for a in attr_value if a])
                elif isinstance(attr_value, str):
                    aliases.append(attr_value)
                break
        
        entities.append({
            "entity_id": entity_id,
            "domain": domain,
            "friendly_name": friendly_name or entity_id,
            "aliases": aliases,
            "state": state.get("state", ""),
        })
    
    return entities


def find_entity_by_alias(alias: str) -> Tuple[Optional[str], List[str]]:
    """Find entity ID by alias using cached entities
    
    Supports three methods:
    1. entity_id: If input contains '.', treat as entity_id directly
    2. friendly_name: Match against entity's friendly_name attribute
    3. aliases: Match against aliases in entity attributes (if available)
    
    Args:
        alias: Alias name or entity ID to search for
    
    Returns:
        Tuple of (first matching entity_id, list of all matching entity_ids)
    """
    # Method 1: If it looks like an entity ID (contains dot), return as-is
    if '.' in alias:
        logger.debug(f"Treating '{alias}' as entity_id")
        return alias, [alias]
    
    cache = get_entity_cache()
    if not cache:
        logger.warning("Entity cache not initialized, cannot find entity by alias")
        return None, []
    
    alias_lower = alias.lower()
    matches = []
    
    for state in cache:
        entity_id = state.get("entity_id", "")
        attributes = state.get("attributes", {})
        friendly_name = attributes.get("friendly_name", "")
        
        # Method 2: Check if alias matches friendly_name (case-insensitive)
        if friendly_name and friendly_name.lower() == alias_lower:
            logger.debug(f"Found entity {entity_id} by friendly_name: {friendly_name}")
            matches.append(entity_id)
            continue
        
        # Method 3: Check if alias matches any attribute that might contain aliases
        # Some integrations store aliases in attributes
        for attr_key, attr_value in attributes.items():
            if attr_key in ["aliases", "alias", "device_aliases"]:
                if isinstance(attr_value, list):
                    for entity_alias in attr_value:
                        if isinstance(entity_alias, str) and entity_alias.lower() == alias_lower:
                            logger.debug(f"Found entity {entity_id} by alias in {attr_key}: {entity_alias}")
                            matches.append(entity_id)
                            break
                elif isinstance(attr_value, str) and attr_value.lower() == alias_lower:
                    logger.debug(f"Found entity {entity_id} by alias in {attr_key}: {attr_value}")
                    matches.append(entity_id)
                    break
        
        # Also check if alias matches part of entity_id (case-insensitive)
        if entity_id.lower().endswith(f".{alias_lower}"):
            logger.debug(f"Found entity {entity_id} by entity_id pattern")
            matches.append(entity_id)
    
    if not matches:
        logger.debug(f"No entity found for alias: {alias}")
        return None, []
    
    # Return first match and all matches
    return matches[0], matches

