"""
Ozon InventoryManager — управление остатками на складах Ozon.
"""

import logging
from typing import List, Dict, Any
from ozon_client import OzonAPI

logger = logging.getLogger(__name__)

class OzonInventoryManager:
    """Управление остатками Ozon (FBS/FBO)"""

    def __init__(self, api: OzonAPI):
        self.api = api

    async def get_stocks(self, limit: int = 1000) -> List[Dict[str, Any]]:
        """
        Получить информацию об остатках на складах.
        Эндпоинт: /v3/product/info/stocks
        """
        data = {
            "filter": {"visibility": "ALL"},
            "limit": limit
        }
        response = await self.api.post("/v3/product/info/stocks", data=data)
        return response.get("result", {}).get("items", [])

    async def update_stocks(self, stocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Обновить остатки на складах (FBS).
        stocks: [{"offer_id": "...", "stock": 10}, ...]
        """
        data = {"stocks": stocks}
        response = await self.api.post("/v1/product/import/stocks", data=data)
        return response.get("result", [])
