"""
Ozon OrdersManager — управление заказами (FBS/FBO).
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from ozon_client import OzonAPI

logger = logging.getLogger(__name__)

class OzonOrdersManager:
    """Управление заказами Ozon"""

    def __init__(self, api: OzonAPI):
        self.api = api

    async def get_fbs_unfulfilled_orders(self) -> List[Dict[str, Any]]:
        """
        Получить список несобранных заказов FBS.
        Эндпоинт: /v3/posting/fbs/unfulfilled/list
        """
        data = {
            "dir": "ASC",
            "filter": {"status": "awaiting_packaging"},
            "limit": 100,
            "offset": 0,
            "with": {"analytics_data": True}
        }
        response = await self.api.post("/v3/posting/fbs/unfulfilled/list", data=data)
        return response.get("result", {}).get("postings", [])

    async def get_fbo_orders(self, date_from: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Получить список заказов FBO за период.
        """
        if not date_from:
            date_from = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
            
        data = {
            "dir": "ASC",
            "filter": {
                "since": date_from,
                "to": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
            },
            "limit": 100
        }
        response = await self.api.post("/v2/posting/fbo/list", data=data)
        return response.get("result", [])
