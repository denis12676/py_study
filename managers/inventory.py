"""
InventoryManager — управление остатками (FBS и FBO).
Склады, остатки FBS, остатки FBO с кешированием.
"""

import logging
import time as time_module
from datetime import datetime
from typing import Dict, Any, List, Optional

from wb_client import WildberriesAPI, API_ENDPOINTS
from cache import APICache
from models import Stock

logger = logging.getLogger(__name__)


class InventoryManager:
    """Управление остатками на складах (FBS и FBO)"""

    def __init__(self, api: WildberriesAPI):
        self.api = api
        self._cache = APICache(ttl=300)

    # ------------------------------------------------------------------
    # FBS — склад продавца
    # ------------------------------------------------------------------

    def get_warehouses(self) -> List[Dict]:
        """Получить список складов продавца."""
        response = self.api.get(
            "/api/v3/warehouses",
            base_url=API_ENDPOINTS["marketplace"]
        )
        return response if isinstance(response, list) else response.get("data", [])

    def get_stocks(self, warehouse_id: int, chrt_ids: Optional[List[int]] = None) -> List[Stock]:
        """
        Получить остатки на конкретном складе продавца (FBS).

        Returns:
            Список моделей Stock
        """
        from managers.products import ProductsManager
        try:
            products_mgr = ProductsManager(self.api)
            # chrt_mapping is {chrtId: {nmId, vendorCode, ...}}
            chrt_mapping = products_mgr.get_chrt_id_mapping()

            if chrt_ids is None:
                chrt_ids = list(chrt_mapping.keys())

            if not chrt_ids:
                return []

            all_stocks = []
            batch_size = 1000

            for i in range(0, len(chrt_ids), batch_size):
                batch = chrt_ids[i:i + batch_size]
                response = self.api.post(
                    f"/api/v3/stocks/{warehouse_id}",
                    data={"chrtIds": batch, "skus": []},
                    base_url=API_ENDPOINTS["marketplace"]
                )

                raw_stocks = response.get('stocks', []) if isinstance(response, dict) else response
                if not isinstance(raw_stocks, list): continue

                for s in raw_stocks:
                    chrt_id = s.get('chrtId')
                    mapping = chrt_mapping.get(chrt_id, {})
                    
                    # Prepare data for model_validate
                    stock_data = {
                        "nmId": mapping.get("nmId") or s.get("nmId") or 0,
                        "supplierArticle": mapping.get("vendorCode") or s.get("vendorCode") or "",
                        "subject": mapping.get("subjectName") or mapping.get("title") or "",
                        "brand": mapping.get("brand") or "",
                        "techSize": mapping.get("techSize") or s.get("techSize") or "",
                        "quantity": s.get("amount", 0),
                        "quantityFull": s.get("amount", 0) + s.get("inTransit", 0),
                        "warehouseName": f"FBS {warehouse_id}"
                    }
                    all_stocks.append(Stock.model_validate(stock_data))

            return all_stocks

        except Exception as e:
            logger.error("Ошибка получения остатков FBS: %s", e)
            return []

    def get_all_fbs_stocks(self) -> Dict[int, List[Stock]]:
        """Получить остатки со всех складов продавца (FBS)."""
        warehouses = self.get_warehouses()
        all_stocks = {}
        for warehouse in warehouses:
            wh_id = warehouse.get('id')
            if wh_id:
                stocks = self.get_stocks(wh_id)
                if stocks:
                    all_stocks[wh_id] = stocks
        return all_stocks

    # ------------------------------------------------------------------
    # FBO — склад Wildberries
    # ------------------------------------------------------------------

    def get_fbo_stocks(self, use_cache: bool = True, force_refresh: bool = False) -> List[Stock]:
        """
        Получить остатки FBO (склад Wildberries) через Statistics API.

        Returns:
            Список моделей Stock
        """
        cache_key = "fbo_stocks_v2"

        if not force_refresh and use_cache:
            cached = self._cache.get(cache_key)
            if cached is not None:
                return [Stock.model_validate(s) for s in cached]

        try:
            # Statistics API
            raw_stocks = self._get_fbo_stocks_statistics()
            if raw_stocks:
                # Statistics API returns nmId, supplierArticle, quantity, etc.
                # Our Stock model handles these aliases.
                models = [Stock.model_validate(s) for s in raw_stocks]
                self._cache.set(cache_key, [m.model_dump() for m in models])
                return models
        except Exception as e:
            logger.warning("FBO Statistics API failed: %s", e)

        return []

    def _get_fbo_stocks_statistics(self) -> List[Dict]:
        all_stocks = []
        date_from = "2019-06-20T00:00:00"
        
        # We limit to 1 iteration for smoke test or simple usage to avoid 429
        # in production you'd loop or use better backoff
        try:
            response = self.api.get(
                "/api/v1/supplier/stocks",
                params={"dateFrom": date_from},
                base_url=self.api.config.statistics_url
            )
            return response if isinstance(response, list) else []
        except:
            return []

    def clear_fbo_cache(self):
        self._cache.clear()
