"""
OrdersManager — управление заказами FBS, DBS.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from wb_client import WildberriesAPI, API_ENDPOINTS
from models import Order

logger = logging.getLogger(__name__)


class OrdersManager:
    """Управление заказами FBS, DBS"""

    def __init__(self, api: WildberriesAPI):
        self.api = api

    def get_new_orders(self, limit: int = 100) -> List[Order]:
        """
        Получить новые заказы для сборки.

        Returns:
            Список моделей Order
        """
        try:
            response = self.api.get(
                "/api/v3/orders",
                params={
                    "limit": limit,
                    "next": 0,
                    "dateFrom": int((datetime.now() - timedelta(days=7)).timestamp())
                },
                base_url=self.api.config.marketplace_url
            )
            orders_raw = response.get("orders", [])
            return [Order.model_validate(o) for o in orders_raw]
        except Exception as e:
            logger.error(f"Error fetching new orders: {e}")
            return []

    def get_order_status(self, order_ids: List[int]) -> List[Dict]:
        """Получить текущие статусы заказов."""
        try:
            response = self.api.post(
                "/api/v3/orders/status",
                data={"orders": order_ids},
                base_url=self.api.config.marketplace_url
            )
            return response.get("orders", [])
        except Exception as e:
            logger.error(f"Error fetching order statuses: {e}")
            return []

    def confirm_assembly(self, order_id: int) -> bool:
        """Подтвердить сборку заказа."""
        try:
            self.api.patch(
                f"/api/v3/orders/{order_id}/confirm",
                base_url=self.api.config.marketplace_url
            )
            return True
        except Exception as e:
            logger.error(f"Error confirming assembly for order {order_id}: {e}")
            return False
