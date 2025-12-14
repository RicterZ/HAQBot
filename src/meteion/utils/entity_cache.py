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
            
            # Try to load registry, but don't fail if it's not available
            registry = {}
            try:
                registry = await client.get_entity_registry()
            except Exception as reg_error:
                logger.warning(f"Failed to load entity registry (may not be available): {reg_error}")
                registry = {}
            
            with _cache_lock:
                _entity_cache = states
                _entity_registry_cache = registry
                _cache_initialized = True
            
            logger.info(f"Entity cache loaded: {len(states)} entities, {len(registry)} registry entries")
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
        
        registry_entry = registry.get(entity_id, {})
        aliases = registry_entry.get("aliases", [])
        
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
    
    Supports three methods:
    1. entity_id: If input contains '.', treat as entity_id directly
    2. friendly_name: Match against entity's friendly_name attribute
    3. alias: Match against entity registry aliases
    
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
        
        # Method 3: Check if alias matches entity registry aliases
        registry_entry = registry.get(entity_id, {})
        aliases = registry_entry.get("aliases", [])
        if aliases:
            for entity_alias in aliases:
                if entity_alias.lower() == alias_lower:
                    logger.debug(f"Found entity {entity_id} by alias: {entity_alias}")
                    return entity_id
        
        # Also check if alias matches part of entity_id (case-insensitive)
        if entity_id.lower().endswith(f".{alias_lower}"):
            logger.debug(f"Found entity {entity_id} by entity_id pattern")
            return entity_id
    
    logger.debug(f"No entity found for alias: {alias}")
    return None

