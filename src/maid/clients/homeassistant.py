import json
import logging
import os
from typing import Optional, Dict, Any, List

import httpx

from maid.utils.logger import logger


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
            
            # Log sample device structure for debugging
            if devices and logger.isEnabledFor(logging.DEBUG):
                sample = devices[0]
                logger.debug(f"Sample device structure: {list(sample.keys())}")
                if "area_id" in sample:
                    logger.debug(f"Sample device area_id: {sample.get('area_id')}")
            
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

    async def get_entity_areas(self) -> Dict[str, str]:
        """Get area information for all entities using template API
        
        Returns:
            Dictionary mapping entity_id to area_name
        """
        template = """
{
  "entities": [
    {%- for entity_id in states | map(attribute='entity_id') | list -%}
    {
      "entity_id": "{{ entity_id }}",
      "area": "{{ area_name(entity_id) if area_name(entity_id) else '' }}"
    }{%- if not loop.last -%},{%- endif -%}
    {%- endfor -%}
  ]
}
"""
        url = "/api/template"
        
        try:
            logger.debug("Fetching entity area information using template API")
            
            response = await self.client.post(url, json={"template": template})
            response.raise_for_status()
            
            result = response.json()
            entities = result.get("entities", [])
            logger.info(f"Received area information for {len(entities)} entities")
            
            # Convert list to dict for easier lookup
            entity_areas = {}
            entities_with_area = 0
            for entity in entities:
                entity_id = entity.get("entity_id")
                area_name = entity.get("area", "")
                if entity_id:
                    entity_areas[entity_id] = area_name
                    if area_name:
                        entities_with_area += 1
            
            logger.info(f"Entity areas: {entities_with_area}/{len(entities)} entities have area")
            if entity_areas:
                # Log a few sample entity IDs to verify format
                sample_ids = list(entity_areas.keys())[:5]
                logger.debug(f"Sample entity IDs with areas: {sample_ids}")
            return entity_areas
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning("Template API not available (404). Cannot get area information.")
                return {}
            logger.error(f"HA template API request failed: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Error getting entity areas: {e}")
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
            # Store both string and original format for compatibility
            areas_dict = {}
            for area in areas:
                area_id = area.get("area_id")
                if area_id:
                    # Store with string key for consistent lookup
                    areas_dict[str(area_id)] = area
                    # Also store with original key if it's different
                    if str(area_id) != area_id:
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

    def _is_device_temperature_sensor(self, entity_id: str, device_id: Optional[str], friendly_name: str, all_states: List[Dict[str, Any]]) -> bool:
        """Check if a temperature sensor belongs to a device (not ambient temperature)
        
        Args:
            entity_id: The temperature sensor entity ID
            device_id: The device ID of the sensor
            friendly_name: The friendly name of the sensor
            all_states: All entity states to check device entities
        
        Returns:
            True if this is a device temperature sensor, False if ambient
        """
        # Keywords that indicate device temperature (not ambient)
        device_keywords = [
            # Chinese keywords
            "插座", "电源", "设备温度", "设备", "电暖器", "加热器", "开关",
            # English keywords
            "outlet", "socket", "plug", "power", "device temperature", "device temp",
            "heater", "switch", "thermostat", "climate"
        ]
        
        # Check entity ID and friendly name for device keywords
        entity_id_lower = entity_id.lower()
        friendly_name_lower = friendly_name.lower()
        
        for keyword in device_keywords:
            if keyword.lower() in entity_id_lower or keyword.lower() in friendly_name_lower:
                return True
        
        if not device_id:
            return False
        
        # Check device name from device cache
        from maid.utils.entity_cache import get_device_cache
        device_cache = get_device_cache() or []
        for device in device_cache:
            if device.get("id") == device_id:
                device_name = device.get("name", "").lower()
                for keyword in device_keywords:
                    if keyword.lower() in device_name:
                        return True
                break
        
        # Device types that typically have device temperature sensors
        device_control_domains = ["climate", "switch", "light", "fan", "heater", "thermostat"]
        
        # Check if any entity in the same device is a control device
        for state in all_states:
            other_entity_id = state.get("entity_id", "")
            if not other_entity_id or other_entity_id == entity_id:
                continue
            
            other_attributes = state.get("attributes", {})
            other_device_id = other_attributes.get("device_id")
            
            if other_device_id == device_id:
                other_domain = other_entity_id.split(".")[0] if "." in other_entity_id else ""
                if other_domain in device_control_domains:
                    return True
        
        return False

    async def get_context_info(self) -> Dict[str, Any]:
        """Get home context information - only important home status
        
        Returns:
            Dictionary containing home context information
        """
        try:
            states = await self.get_states()
            
            context = {
                "lights_on": [],
                "climate": [],
                "temperature_sensors": [],
                "humidity_sensors": [],
                "air_quality_sensors": [],
                "energy_sensors": [],
                "weather": [],
                "important_binary_sensors": []
            }
            
            for state in states:
                entity_id = state.get("entity_id", "")
                if not entity_id:
                    continue
                
                domain = entity_id.split(".")[0] if "." in entity_id else "unknown"
                attributes = state.get("attributes", {})
                friendly_name = attributes.get("friendly_name", "") or entity_id
                entity_state = state.get("state", "").lower()
                
                if domain == "light" and entity_state == "on":
                    brightness = attributes.get("brightness")
                    brightness_pct = round((brightness / 255) * 100) if brightness else None
                    context["lights_on"].append({
                        "friendly_name": friendly_name,
                        "brightness": brightness_pct
                    })
                
                elif domain == "climate":
                    current_temp = attributes.get("current_temperature")
                    target_temp = attributes.get("temperature")
                    hvac_mode = attributes.get("hvac_mode", entity_state)
                    fan_mode = attributes.get("fan_mode")
                    
                    context["climate"].append({
                        "friendly_name": friendly_name,
                        "hvac_mode": hvac_mode,
                        "current_temp": current_temp,
                        "target_temp": target_temp,
                        "fan_mode": fan_mode
                    })
                
                elif domain == "sensor":
                    unit = attributes.get("unit_of_measurement", "")
                    device_class = attributes.get("device_class", "")
                    device_id = attributes.get("device_id")
                    
                    if device_class == "temperature" or "temperature" in entity_id.lower():
                        # Filter out device temperature sensors (e.g., heater device temperature, socket temperature)
                        if not self._is_device_temperature_sensor(entity_id, device_id, friendly_name, states):
                            context["temperature_sensors"].append({
                                "entity_id": entity_id,
                                "friendly_name": friendly_name,
                                "value": entity_state,
                                "unit": unit or "°C",
                                "device_id": device_id
                            })
                    elif device_class == "humidity" or "humidity" in entity_id.lower():
                        context["humidity_sensors"].append({
                            "friendly_name": friendly_name,
                            "value": entity_state,
                            "unit": unit or "%"
                        })
                    elif device_class in ["aqi", "pm25", "pm10", "co2", "co", "no2", "o3"] or "air_quality" in entity_id.lower() or "aqi" in entity_id.lower():
                        context["air_quality_sensors"].append({
                            "friendly_name": friendly_name,
                            "value": entity_state,
                            "unit": unit or "",
                            "device_class": device_class
                        })
                    elif device_class == "energy" or "energy" in entity_id.lower() or "consumption" in entity_id.lower() or "daily" in entity_id.lower():
                        # Check if it's daily energy consumption (not instantaneous power)
                        if "daily" in entity_id.lower() or "day" in friendly_name.lower() or "日" in friendly_name:
                            context["energy_sensors"].append({
                                "friendly_name": friendly_name,
                                "value": entity_state,
                                "unit": unit or "kWh"
                            })
                
                elif domain == "weather":
                    temperature = attributes.get("temperature")
                    condition = attributes.get("condition", entity_state)
                    humidity = attributes.get("humidity")
                    
                    context["weather"].append({
                        "friendly_name": friendly_name,
                        "temperature": temperature,
                        "condition": condition,
                        "humidity": humidity
                    })
                
                elif domain == "binary_sensor":
                    device_class = attributes.get("device_class", "")
                    if device_class in ["door", "window", "motion", "occupancy", "smoke", "gas", "moisture"]:
                        if entity_state == "on":
                            context["important_binary_sensors"].append({
                                "friendly_name": friendly_name,
                                "device_class": device_class,
                                "state": entity_state
                            })
            
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
        from maid.utils.entity_cache import find_entity_by_alias as cache_find
        
        # Use cached lookup
        return cache_find(alias)

    async def close(self):
        await self.client.aclose()

