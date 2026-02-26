import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional, List

import httpx
from pydantic import BaseModel

logger = logging.getLogger(__name__)

@dataclass
class WBConfig:
    api_token: str
    base_url: str = "https://common-api.wildberries.ru"
    content_url: str = "https://content-api.wildberries.ru"
    statistics_url: str = "https://statistics-api.wildberries.ru"
    advert_url: str = "https://advert-api.wildberries.ru"
    marketplace_url: str = "https://marketplace-api.wildberries.ru"

API_ENDPOINTS = {
    "prices": "https://discounts-prices-api.wildberries.ru",
    "content": "https://content-api.wildberries.ru",
    "statistics": "https://statistics-api.wildberries.ru",
    "advert": "https://advert-api.wildberries.ru",
    "marketplace": "https://marketplace-api.wildberries.ru",
    "tariffs": "https://common-api.wildberries.ru",
    "analytics": "https://analytics-api.wildberries.ru"
}

class WildberriesAPI:
    """Асинхронный клиент для Wildberries API"""
    
    def __init__(self, config: WBConfig):
        self.config = config
        self.headers = {
            "Authorization": f"Bearer {config.api_token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        # Семафор для ограничения параллельных запросов (защита от 429)
        self._semaphore = asyncio.Semaphore(5) 
        self._async_client: Optional[httpx.AsyncClient] = None

    async def get_client(self) -> httpx.AsyncClient:
        """Ленивая инициализация асинхронного клиента"""
        if self._async_client is None or self._async_client.is_closed:
            self._async_client = httpx.AsyncClient(
                headers=self.headers,
                timeout=httpx.Timeout(30.0, connect=10.0),
                follow_redirects=True
            )
        return self._async_client

    async def aget(self, endpoint: str, params: Optional[Dict] = None, base_url: str = None) -> Any:
        """Асинхронный GET запрос"""
        url = f"{base_url or self.config.base_url}{endpoint}"
        client = await self.get_client()
        
        async with self._semaphore:
            try:
                response = await client.get(url, params=params)
                return self._handle_response(response)
            except Exception as e:
                logger.error(f"Async GET Error [{url}]: {e}")
                raise

    async def apost(self, endpoint: str, data: Optional[Dict] = None, base_url: str = None) -> Any:
        """Асинхронный POST запрос"""
        url = f"{base_url or self.config.base_url}{endpoint}"
        client = await self.get_client()
        
        async with self._semaphore:
            try:
                response = await client.post(url, json=data)
                return self._handle_response(response)
            except Exception as e:
                logger.error(f"Async POST Error [{url}]: {e}")
                raise

    def _handle_response(self, response: httpx.Response) -> Any:
        if response.status_code == 429:
            logger.warning("Rate limit exceeded (429).")
            # В асинхронной версии тут можно добавить логику ожидания
        
        response.raise_for_status()
        try:
            return response.json()
        except:
            return response.text

    # Синхронные обертки для совместимости
    def get(self, *args, **kwargs):
        import requests
        url = f"{kwargs.get('base_url', self.config.base_url)}{args[0]}"
        resp = requests.get(url, headers=self.headers, params=kwargs.get('params'))
        return resp.json()

    def post(self, *args, **kwargs):
        import requests
        url = f"{kwargs.get('base_url', self.config.base_url)}{args[0]}"
        resp = requests.post(url, headers=self.headers, json=kwargs.get('data'))
        return resp.json()

    async def close(self):
        """Закрыть клиент"""
        if self._async_client:
            await self._async_client.aclose()
