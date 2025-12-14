"""Entity cache for Home Assistant entities"""
from typing import Optional, Dict, Any, List
from threading import Lock

from meteion.utils.logger import logger

# Global cache
_entity_cache: Optional[List[Dict[str, Any]]] = None
_entity_registry_cache: Optional[Dict[str, Dict[str, Any]]] = None
_cache_lock = Lock()
_cache_initialized = False


async def load_entity_cache() -> bool:
    """Load entity cache from Home Assistant
    
    Returns:
        True if cache loaded successfully, False otherwise
    """
    global _entity_cache, _entity_registry_cache, _cache_initialized
    
    try:
        # Import here to avoid circular dependency
        from meteion.clients.homeassistant import HomeAssistantClient
        
        client = HomeAssistantClient()
        try:
            logger.info("Loading entity cache from Home Assistant...")
            states = await client.get_states()
            
            with _cache_lock:
                _entity_cache = states
                _entity_registry_cache = {}  # Not used, kept for compatibility
                _cache_initialized = True
            
            logger.info(f"Entity cache loaded: {len(states)} entities")
            return True
        finally:
            await client.close()
    except Exception as e:
        logger.error(f"Failed to load entity cache: {e}", exc_info=True)
        return False


def get_entity_cache() -> Optional[List[Dict[str, Any]]]:
    """Get cached entity list
    
    Returns:
        Cached entity list or None if not initialized
    """
    with _cache_lock:
        return _entity_cache


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


def find_entity_by_alias(alias: str) -> Optional[str]:
    """Find entity ID by alias using cached entities
    
    Supports two methods:
    1. entity_id: If input contains '.', treat as entity_id directly
    2. friendly_name: Match against entity's friendly_name attribute
    
    Args:
        alias: Alias name or entity ID to search for
    
    Returns:
        Entity ID if found, None otherwise
    """
    # Method 1: If it looks like an entity ID (contains dot), return as-is
    if '.' in alias:
        logger.debug(f"Treating '{alias}' as entity_id")
        return alias
    
    cache = get_entity_cache()
    if not cache:
        logger.warning("Entity cache not initialized, cannot find entity by alias")
        return None
    
    alias_lower = alias.lower()
    
    # Method 2 & 3: Search by friendly_name and aliases
    with _cache_lock:
        registry = _entity_registry_cache or {}
    
    for state in cache:
        entity_id = state.get("entity_id", "")
        attributes = state.get("attributes", {})
        friendly_name = attributes.get("friendly_name", "")
        
        # Method 2: Check if alias matches friendly_name (case-insensitive)
        if friendly_name and friendly_name.lower() == alias_lower:
            logger.debug(f"Found entity {entity_id} by friendly_name: {friendly_name}")
            return entity_id
        
        # Method 3: Check if alias matches any attribute that might contain aliases
        # Some integrations store aliases in attributes
        for attr_key, attr_value in attributes.items():
            if attr_key in ["aliases", "alias", "device_aliases"]:
                if isinstance(attr_value, list):
                    for entity_alias in attr_value:
                        if isinstance(entity_alias, str) and entity_alias.lower() == alias_lower:
                            logger.debug(f"Found entity {entity_id} by alias in {attr_key}: {entity_alias}")
                            return entity_id
                elif isinstance(attr_value, str) and attr_value.lower() == alias_lower:
                    logger.debug(f"Found entity {entity_id} by alias in {attr_key}: {attr_value}")
                    return entity_id
        
        # Also check if alias matches part of entity_id (case-insensitive)
        if entity_id.lower().endswith(f".{alias_lower}"):
            logger.debug(f"Found entity {entity_id} by entity_id pattern")
            return entity_id
    
    logger.debug(f"No entity found for alias: {alias}")
    return None

