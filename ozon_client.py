import asyncio
import logging
from typing import Any, Dict, Optional
import httpx

logger = logging.getLogger(__name__)

class OzonConfig:
    """Конфигурация для Ozon API"""
    def __init__(self, client_id: str, api_key: str):
        self.client_id = client_id
        self.api_key = api_key
        self.base_url = "https://api-seller.ozon.ru"

class OzonAPI:
    """Асинхронный клиент для Ozon API"""
    
    def __init__(self, config: OzonConfig):
        self.config = config
        self.headers = {
            "Client-Id": config.client_id,
            "Api-Key": config.api_key,
            "Content-Type": "application/json"
        }
        self._semaphore = asyncio.Semaphore(5)
        self._async_client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._async_client is None or self._async_client.is_closed:
            self._async_client = httpx.AsyncClient(
                headers=self.headers,
                timeout=httpx.Timeout(30.0),
                base_url=self.config.base_url
            )
        return self._async_client

    async def post(self, endpoint: str, data: Optional[Dict] = None) -> Any:
        """Ozon API почти всегда использует POST для получения данных"""
        client = await self._get_client()
        async with self._semaphore:
            try:
                response = await client.post(endpoint, json=data or {})
                response.raise_for_status()
                return response.json()
            except Exception as e:
                logger.error(f"Ozon API POST Error [{endpoint}]: {e}")
                raise

    async def close(self):
        if self._async_client:
            await self._async_client.aclose()
