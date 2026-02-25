"""
OrdersManager — управление заказами FBS, DBS.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List

from wb_client import WildberriesAPI

logger = logging.getLogger(__name__)


class OrdersManager:
    """Управление заказами FBS, DBS"""

    def __init__(self, api: WildberriesAPI):
        self.api = api

    def get_new_orders(self, limit: int = 100) -> List[Dict]:
        """
        Получить новые заказы для сборки.

        Args:
            limit: Лимит заказов

        Returns:
            Список заказов
        """
        response = self.api.get(
            "/api/v3/orders",
            params={
                "limit": limit,
                "dateFrom": (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
            },
            base_url=self.api.config.marketplace_url
        )
        return response.get("orders", [])

    def confirm_assembly(self, order_id: int) -> bool:
        """
        Подтвердить сборку заказа.

        Args:
            order_id: ID заказа

        Returns:
            True если успешно
        """
        try:
            self.api.patch(
                f"/api/v3/orders/{order_id}/confirm",
                base_url=self.api.config.marketplace_url
            )
            return True
        except Exception as e:
            logger.error("Ошибка подтверждения сборки заказа %d: %s", order_id, e)
            return False

    def cancel_order(self, order_id: int, reason: str = "Нет в наличии") -> bool:
        """
        Отменить заказ.

        Args:
            order_id: ID заказа
            reason: Причина отмены

        Returns:
            True если успешно
        """
        try:
            self.api.patch(
                f"/api/v3/orders/{order_id}/cancel",
                data={"reason": reason},
                base_url=self.api.config.marketplace_url
            )
            return True
        except Exception as e:
            logger.error("Ошибка отмены заказа %d: %s", order_id, e)
            return False
