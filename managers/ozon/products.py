"""
Ozon ProductsManager — управление товарами на Ozon.
"""

import logging
from typing import List, Dict, Any
from ozon_client import OzonAPI

logger = logging.getLogger(__name__)

class OzonProductsManager:
    """Управление товарами Ozon"""

    def __init__(self, api: OzonAPI):
        self.api = api

    async def get_product_list(self, limit: int = 100) -> List[int]:
        """Получить список ID товаров (product_id)"""
        data = {
            "filter": {"visibility": "ALL"},
            "limit": limit
        }
        response = await self.api.post("/v2/product/list", data=data)
        items = response.get("result", {}).get("items", [])
        return [item["product_id"] for item in items]

    async def get_products_details(self, product_ids: List[int]) -> List[Dict[str, Any]]:
        """Получить детальную информацию по списку ID"""
        if not product_ids:
            return []
            
        data = {
            "product_id": product_ids
        }
        response = await self.api.post("/v2/product/info/list", data=data)
        return response.get("result", {}).get("items", [])

    async def get_all_products(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Комбинированный метод: список + детали"""
        ids = await self.get_product_list(limit=limit)
        return await self.get_products_details(ids)
