"""
AdvertisingManager — управление рекламными кампаниями.
"""

import logging
from typing import Dict, List, Optional

from wb_client import WildberriesAPI

logger = logging.getLogger(__name__)


class AdvertisingManager:
    """Управление рекламными кампаниями"""

    def __init__(self, api: WildberriesAPI):
        self.api = api

    def get_campaigns(self, status: Optional[int] = None) -> List[Dict]:
        """
        Получить список рекламных кампаний.

        Args:
            status: Фильтр по статусу (4-готова к запуску, 7-активна, 11-пауза)

        Returns:
            Список кампаний
        """
        params = {}
        if status is not None:
            params["status"] = status

        response = self.api.get(
            "/adv/v1/promotion/adverts",
            params=params,
            base_url=self.api.config.advert_url
        )
        return response.get("adverts", [])

    def get_campaign_stats(self, campaign_ids: List[int]) -> List[Dict]:
        """
        Получить статистику по кампаниям.

        Args:
            campaign_ids: Список ID кампаний

        Returns:
            Статистика по каждой кампании
        """
        response = self.api.get(
            "/adv/v3/fullstats",
            params={"id": campaign_ids},
            base_url=self.api.config.advert_url
        )
        return response if isinstance(response, list) else []

    def create_campaign(
        self,
        name: str,
        nm_ids: List[int],
        campaign_type: int = 6,
        bid: int = 50
    ) -> Dict:
        """
        Создать рекламную кампанию.

        Args:
            name: Название кампании
            nm_ids: Артикулы товаров для продвижения
            campaign_type: Тип (4-каталог, 5-карточка, 6-поиск, 7-рекомендации)
            bid: Ставка в рублях

        Returns:
            Информация о созданной кампании
        """
        return self.api.post(
            "/adv/v2/seacat/save-ad",
            data={
                "name": name,
                "nms": nm_ids,
                "type": campaign_type,
                "bid": bid
            },
            base_url=self.api.config.advert_url
        )

    def update_bid(self, campaign_ids: List[int], bid: int) -> bool:
        """
        Обновить ставку для кампаний.

        Args:
            campaign_ids: Список ID кампаний
            bid: Новая ставка

        Returns:
            True если успешно
        """
        try:
            self.api.patch(
                "/api/advert/v1/bids",
                data={
                    "advertIds": campaign_ids,
                    "bid": bid
                },
                base_url=self.api.config.advert_url
            )
            return True
        except Exception as e:
            logger.error("Ошибка обновления ставки: %s", e)
            return False

    def pause_campaign(self, campaign_id: int) -> bool:
        """Приостановить кампанию"""
        try:
            self.api.get(
                "/adv/v0/pause",
                params={"id": campaign_id},
                base_url=self.api.config.advert_url
            )
            return True
        except Exception as e:
            logger.error("Ошибка паузы кампании %d: %s", campaign_id, e)
            return False

    def start_campaign(self, campaign_id: int) -> bool:
        """Запустить кампанию"""
        try:
            self.api.get(
                "/adv/v0/start",
                params={"id": campaign_id},
                base_url=self.api.config.advert_url
            )
            return True
        except Exception as e:
            logger.error("Ошибка запуска кампании %d: %s", campaign_id, e)
            return False

    def delete_campaign(self, campaign_id: int) -> bool:
        """Удалить кампанию"""
        try:
            self.api.get(
                "/adv/v0/delete",
                params={"id": campaign_id},
                base_url=self.api.config.advert_url
            )
            return True
        except Exception as e:
            logger.error("Ошибка удаления кампании %d: %s", campaign_id, e)
            return False

    def get_budget(self, campaign_id: int) -> Dict:
        """
        Получить бюджет кампании.

        Returns:
            Информация о бюджете
        """
        return self.api.get(
            "/adv/v1/budget",
            params={"id": campaign_id},
            base_url=self.api.config.advert_url
        )
