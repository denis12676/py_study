"""
AdvertisingManager — управление рекламными кампаниями.
"""

import logging
from typing import Dict, List, Optional

from wb_client import WildberriesAPI, API_ENDPOINTS
from models import Campaign

logger = logging.getLogger(__name__)


class AdvertisingManager:
    """Управление рекламными кампаниями"""

    def __init__(self, api: WildberriesAPI):
        self.api = api

    def get_campaigns(self, status: Optional[int] = None) -> List[Campaign]:
        """
        Получить список рекламных кампаний.

        Returns:
            Список моделей Campaign
        """
        params = {}
        if status is not None:
            params["status"] = status

        try:
            response = self.api.get(
                "/adv/v1/promotion/adverts",
                params=params,
                base_url=self.api.config.advert_url
            )
            # Response is often a list directly or wrapped in 'adverts'
            adverts = response if isinstance(response, list) else response.get("adverts", [])
            return [Campaign.model_validate(adv) for adv in adverts]
        except Exception as e:
            logger.error(f"Error fetching campaigns: {e}")
            return []

    def get_campaign_stats(self, campaign_ids: List[int]) -> List[Dict]:
        """Получить детальную статистику по кампаниям."""
        try:
            response = self.api.get(
                "/adv/v2/fullstats",
                params={"id": campaign_ids},
                base_url=self.api.config.advert_url
            )
            return response if isinstance(response, list) else []
        except Exception as e:
            logger.error(f"Error fetching campaign stats: {e}")
            return []

    def update_bid(self, campaign_id: int, bid: int) -> bool:
        """Обновить ставку для кампании."""
        try:
            self.api.post(
                "/adv/v1/save-cpm",
                data={
                    "advertId": campaign_id,
                    "type": 6, # По умолчанию Поиск, можно расширить
                    "cpm": bid
                },
                base_url=self.api.config.advert_url
            )
            return True
        except Exception as e:
            logger.error(f"Error updating bid for {campaign_id}: {e}")
            return False

    def pause_campaign(self, campaign_id: int) -> bool:
        """Приостановить кампанию."""
        try:
            self.api.get(
                "/adv/v0/pause",
                params={"id": campaign_id},
                base_url=self.api.config.advert_url
            )
            return True
        except Exception as e:
            logger.error(f"Error pausing campaign {campaign_id}: {e}")
            return False

    def start_campaign(self, campaign_id: int) -> bool:
        """Запустить кампанию."""
        try:
            self.api.get(
                "/adv/v0/start",
                params={"id": campaign_id},
                base_url=self.api.config.advert_url
            )
            return True
        except Exception as e:
            logger.error(f"Error starting campaign {campaign_id}: {e}")
            return False

    def get_budget(self, campaign_id: int) -> float:
        """Получить текущий бюджет кампании."""
        try:
            response = self.api.get(
                "/adv/v1/budget",
                params={"id": campaign_id},
                base_url=self.api.config.advert_url
            )
            return float(response.get("cash", 0) or 0)
        except:
            return 0.0
