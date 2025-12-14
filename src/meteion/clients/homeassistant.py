import json
import os
from typing import Optional, Dict, Any

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
            
            response = await self.client.post(url, json=payload)
            response.raise_for_status()
            
            result = response.json()
            logger.info(f"Received HA response (status: {response.status_code})")
            
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
            
            response = await self.client.post(url, json=payload)
            response.raise_for_status()
            
            result = response.json()
            logger.info(f"Service call successful (status: {response.status_code})")
            
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
            
            response = await self.client.post(url, json=payload)
            response.raise_for_status()
            
            result = response.json()
            logger.info(f"Received live context (status: {response.status_code})")
            
            return result
        except httpx.HTTPStatusError as e:
            logger.error(f"HA GetLiveContext request failed: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Error getting live context: {e}")
            raise

    async def close(self):
        await self.client.aclose()

