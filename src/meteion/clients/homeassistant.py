import json
import os
from typing import Optional, Dict, Any, List

import httpx

from meteion.utils.logger import logger


class HomeAssistantClient:
    def __init__(self):
        self.base_url = os.getenv("HA_URL", "http://homeassistant:8123")
        self.token = os.getenv("HA_TOKEN", "")
        self.agent_id = os.getenv("HA_AGENT_ID", "conversant.ollama_conversation")
        
        if not self.token:
            raise ValueError("HA_TOKEN environment variable is not set")
        
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers=self.headers,
            timeout=600.0,
        )

    async def process_conversation(
        self, 
        text: str, 
        agent_id: Optional[str] = None,
        language: Optional[str] = None,
        conversation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        if agent_id is None:
            agent_id = self.agent_id
        
        payload = {
            "text": text,
        }
        
        if agent_id:
            payload["agent_id"] = agent_id
        
        if language:
            payload["language"] = language
        
        if conversation_id:
            payload["conversation_id"] = conversation_id
        
        url = "/api/conversation/process"
        
        try:
            logger.info(f"Sending conversation request to HA: {text[:50]}...")
            logger.debug(f"Request payload: {json.dumps(payload, ensure_ascii=False, indent=2)}")
            
            response = await self.client.post(url, json=payload)
            response.raise_for_status()
            
            result = response.json()
            logger.info(f"Received HA response (status: {response.status_code})")
            logger.debug(f"HA response content: {json.dumps(result, ensure_ascii=False, indent=2)}")
            
            return result
        except httpx.HTTPStatusError as e:
            logger.error(f"HA API request failed: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Error processing conversation request: {e}")
            raise

    async def call_service(
        self,
        domain: str,
        service: str,
        entity_id: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Call Home Assistant service
        
        Args:
            domain: Service domain (e.g., 'switch', 'light')
            service: Service name (e.g., 'turn_on', 'turn_off')
            entity_id: Entity ID (optional)
            **kwargs: Other service parameters
        """
        url = f"/api/services/{domain}/{service}"
        payload = {}
        
        if entity_id:
            payload["entity_id"] = entity_id
        
        if kwargs:
            payload.update(kwargs)
        
        try:
            logger.info(f"Calling HA service: {domain}.{service} with entity_id={entity_id}")
            logger.debug(f"Service call payload: {json.dumps(payload, ensure_ascii=False, indent=2)}")
            
            response = await self.client.post(url, json=payload)
            response.raise_for_status()
            
            result = response.json()
            logger.info(f"Service call successful (status: {response.status_code})")
            logger.debug(f"Service call response: {json.dumps(result, ensure_ascii=False, indent=2)}")
            
            return result
        except httpx.HTTPStatusError as e:
            logger.error(f"HA service call failed: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Error calling HA service: {e}")
            raise

    async def get_live_context(
        self,
        agent_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get live context information (GetLiveContext)
        
        Args:
            agent_id: Conversation agent ID (optional, defaults to configured agent_id)
        """
        if agent_id is None:
            agent_id = self.agent_id
        
        url = "/api/conversation/process"
        payload = {
            "text": "GetLiveContext",
            "agent_id": agent_id,
        }
        
        try:
            logger.info(f"Requesting live context from HA agent: {agent_id}")
            logger.debug(f"GetLiveContext payload: {json.dumps(payload, ensure_ascii=False, indent=2)}")
            
            response = await self.client.post(url, json=payload)
            response.raise_for_status()
            
            result = response.json()
            logger.info(f"Received live context (status: {response.status_code})")
            logger.debug(f"Live context response: {json.dumps(result, ensure_ascii=False, indent=2)}")
            
            return result
        except httpx.HTTPStatusError as e:
            logger.error(f"HA GetLiveContext request failed: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Error getting live context: {e}")
            raise

    async def get_states(self) -> List[Dict[str, Any]]:
        """Get all entity states from Home Assistant
        
        Returns:
            List of entity state dictionaries
        """
        url = "/api/states"
        
        try:
            logger.debug("Fetching all entity states from HA")
            
            response = await self.client.get(url)
            response.raise_for_status()
            
            states = response.json()
            logger.debug(f"Received {len(states)} entity states")
            
            return states
        except httpx.HTTPStatusError as e:
            logger.error(f"HA get_states request failed: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Error getting states: {e}")
            raise

    async def get_devices(self) -> List[Dict[str, Any]]:
        """Get all devices from Home Assistant
        
        Returns:
            List of device dictionaries
        """
        url = "/api/config/device_registry/list"
        
        try:
            logger.debug("Fetching all devices from HA")
            
            response = await self.client.get(url)
            response.raise_for_status()
            
            devices = response.json()
            logger.debug(f"Received {len(devices)} devices")
            
            return devices
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.debug("Device registry API not available, will extract from states")
                return []
            logger.error(f"HA get_devices request failed: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Error getting devices: {e}")
            raise

    async def get_areas(self) -> Dict[str, Dict[str, Any]]:
        """Get all areas from Home Assistant
        
        Returns:
            Dictionary mapping area_id to area information
        """
        url = "/api/config/area_registry/list"
        
        try:
            logger.debug("Fetching all areas from HA")
            
            response = await self.client.get(url)
            response.raise_for_status()
            
            areas = response.json()
            logger.debug(f"Received {len(areas)} areas")
            
            # Convert list to dict for easier lookup
            areas_dict = {}
            for area in areas:
                area_id = area.get("area_id")
                if area_id:
                    areas_dict[area_id] = area
            
            return areas_dict
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.debug("Area registry API not available")
                return {}
            logger.error(f"HA get_areas request failed: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Error getting areas: {e}")
            raise

    async def get_context_info(self) -> Dict[str, Any]:
        """Get context information directly from API without using conversation
        
        Returns:
            Dictionary containing context information
        """
        try:
            # Get all states
            states = await self.get_states()
            
            # Categorize entities
            context = {
                "total_entities": len(states),
                "sensors": [],
                "switches": [],
                "lights": [],
                "climate": [],
                "binary_sensors": [],
                "other": []
            }
            
            for state in states:
                entity_id = state.get("entity_id", "")
                if not entity_id:
                    continue
                
                domain = entity_id.split(".")[0] if "." in entity_id else "unknown"
                attributes = state.get("attributes", {})
                friendly_name = attributes.get("friendly_name", "") or entity_id
                entity_state = state.get("state", "")
                
                entity_info = {
                    "entity_id": entity_id,
                    "friendly_name": friendly_name,
                    "state": entity_state
                }
                
                if domain == "sensor":
                    # Add unit if available
                    unit = attributes.get("unit_of_measurement", "")
                    if unit:
                        entity_info["unit"] = unit
                    context["sensors"].append(entity_info)
                elif domain == "switch":
                    context["switches"].append(entity_info)
                elif domain == "light":
                    context["lights"].append(entity_info)
                elif domain == "climate":
                    context["climate"].append(entity_info)
                elif domain == "binary_sensor":
                    context["binary_sensors"].append(entity_info)
                else:
                    context["other"].append(entity_info)
            
            return context
        except Exception as e:
            logger.error(f"Error getting context info: {e}")
            raise

    async def find_entity_by_alias(self, alias: str) -> Optional[str]:
        """Find entity ID by alias (friendly_name or entity_id)
        
        This method now uses the cached entity list for better performance.
        
        Args:
            alias: Alias name or entity ID to search for
        
        Returns:
            Entity ID if found, None otherwise
        """
        from meteion.utils.entity_cache import find_entity_by_alias as cache_find
        
        # Use cached lookup
        return cache_find(alias)

    async def close(self):
        await self.client.aclose()

