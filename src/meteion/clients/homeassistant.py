import json
import os
from typing import Optional, Dict, Any

import httpx

from meteion.utils.logger import logger


class HomeAssistantClient:
    """Home Assistant API client"""

    def __init__(self):
        self.base_url = os.getenv("HA_URL", "http://homeassistant:8123")
        self.token = os.getenv("HA_TOKEN", "")
        self.agent_id = os.getenv("HA_AGENT_ID", "conversant.ollama_conversation")
        self.conversation_id: Optional[str] = None
        
        if not self.token:
            raise ValueError("HA_TOKEN environment variable is not set")
        
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers=self.headers,
            timeout=120.0,
        )

    async def process_conversation(
        self, 
        text: str, 
        agent_id: Optional[str] = None,
        language: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process conversation request
        
        Args:
            text: User input text
            agent_id: Conversation agent ID, defaults to the one configured in environment variable
            language: Language of the input sentence (optional)
            
        Returns:
            Conversation response result containing conversation_id
        """
        if agent_id is None:
            agent_id = self.agent_id
        
        payload = {
            "text": text,
        }
        
        if agent_id:
            payload["agent_id"] = agent_id
        
        if language:
            payload["language"] = language
        
        if self.conversation_id:
            payload["conversation_id"] = self.conversation_id
        
        url = "/api/conversation/process"
        
        try:
            logger.info(f"Sending conversation request to HA: {text[:50]}...")
            
            response = await self.client.post(url, json=payload)
            response.raise_for_status()
            
            result = response.json()
            logger.info(f"Received HA response (status: {response.status_code})")
            
            if isinstance(result, dict) and "conversation_id" in result:
                new_conversation_id = result["conversation_id"]
                
                if self.conversation_id != new_conversation_id:
                    if self.conversation_id is None:
                        logger.info(f"Started new conversation: {new_conversation_id}")
                    else:
                        logger.info(f"Conversation ID updated: {self.conversation_id} -> {new_conversation_id}")
                    self.conversation_id = new_conversation_id
            
            return result
        except httpx.HTTPStatusError as e:
            logger.error(f"HA API request failed: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Error processing conversation request: {e}")
            raise

    async def close(self):
        """Close client connection"""
        await self.client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

