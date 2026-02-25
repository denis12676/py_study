"""
InventoryManager — управление остатками (FBS и FBO).
Склады, остатки FBS, остатки FBO с кешированием.
"""

import logging
import time as time_module
from datetime import datetime
from typing import Dict, Any, List

from wb_client import WildberriesAPI, API_ENDPOINTS
from cache import APICache

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
        """
        Получить список складов продавца.

        Returns:
            Список складов
        """
        response = self.api.get(
            "/api/v3/warehouses",
            base_url=API_ENDPOINTS["marketplace"]
        )
        return response if isinstance(response, list) else response.get("data", [])

    def get_stocks(self, warehouse_id: int, chrt_ids: List[int] = None) -> List[Dict]:
        """
        Получить остатки на конкретном складе продавца (FBS).

        Args:
            warehouse_id: ID склада продавца
            chrt_ids: Список ID размеров товаров. Если None — получает автоматически.

        Returns:
            Остатки товаров с информацией о товаре
        """
        from managers.products import ProductsManager
        try:
            products_mgr = ProductsManager(self.api)
            chrt_mapping = products_mgr.get_chrt_id_mapping()

            if chrt_ids is None:
                chrt_ids = list(chrt_mapping.keys())

            if not chrt_ids:
                logger.warning("Нет chrtIds для запроса остатков")
                return []

            all_stocks = []
            batch_size = 1000

            for i in range(0, len(chrt_ids), batch_size):
                batch = chrt_ids[i:i + batch_size]

                payload = {
                    "chrtIds": batch,
                    "skus": []
                }

                response = self.api.post(
                    f"/api/v3/stocks/{warehouse_id}",
                    data=payload,
                    base_url=API_ENDPOINTS["marketplace"]
                )

                if isinstance(response, dict):
                    stocks = response.get('stocks', [])
                    for stock in stocks:
                        chrt_id = stock.get('chrtId')
                        if chrt_id and chrt_id in chrt_mapping:
                            stock.update(chrt_mapping[chrt_id])
                        else:
                            stock['nmId'] = None
                            stock['vendorCode'] = ''
                            stock['title'] = ''
                            stock['brand'] = ''
                    all_stocks.extend(stocks)
                elif isinstance(response, list):
                    all_stocks.extend(response)

            return all_stocks

        except Exception as e:
            logger.error("Ошибка получения остатков: %s", e, exc_info=True)
            return []

    def get_all_fbs_stocks(self) -> Dict[int, List[Dict]]:
        """
        Получить остатки со всех складов продавца (FBS).

        Returns:
            Словарь {warehouse_id: [остатки]}
        """
        from managers.products import ProductsManager
        try:
            warehouses = self.get_warehouses()
            if not warehouses:
                logger.warning("Нет складов FBS")
                return {}

            products_mgr = ProductsManager(self.api)
            chrt_ids = products_mgr.get_all_chrt_ids()
            if not chrt_ids:
                logger.warning("Нет chrtIds")
                return {}

            logger.info("Получено %d chrtIds для %d складов", len(chrt_ids), len(warehouses))

            all_stocks = {}
            for warehouse in warehouses:
                wh_id = warehouse.get('id')
                wh_name = warehouse.get('name', 'Unknown')
                if wh_id:
                    stocks = self.get_stocks(wh_id, chrt_ids)
                    if stocks:
                        all_stocks[wh_id] = stocks
                        logger.info("Склад %s: %d товаров", wh_name, len(stocks))

            return all_stocks

        except Exception as e:
            logger.error("Ошибка получения всех остатков FBS: %s", e, exc_info=True)
            return {}

    def get_total_stocks_by_product(self) -> Dict[int, Dict]:
        """
        Получить суммарные остатки FBS + FBO для каждого товара.

        Returns:
            Словарь {nmId: {'fbs': сумма, 'fbo': сумма, 'total': сумма, 'details': {...}}}
        """
        result = {}

        try:
            fbs_stocks = self.get_all_fbs_stocks()

            for wh_id, stocks in fbs_stocks.items():
                for stock in stocks:
                    nm_id = stock.get('nmId')
                    amount = stock.get('amount', 0)

                    if nm_id not in result:
                        result[nm_id] = {
                            'fbs': 0,
                            'fbo': 0,
                            'total': 0,
                            'details': {
                                'name': stock.get('name', ''),
                                'article': stock.get('article', ''),
                                'warehouses': {}
                            }
                        }

                    result[nm_id]['fbs'] += amount
                    result[nm_id]['details']['warehouses'][wh_id] = amount

            # FBO
            fbo_data = self.get_fbo_stocks()
            fbo_regions = fbo_data.get('regions', [])

            for region in fbo_regions:
                for office in region.get('offices', []):
                    pass

            for nm_id in result:
                result[nm_id]['total'] = result[nm_id]['fbs'] + result[nm_id]['fbo']

            return result

        except Exception as e:
            logger.error("Ошибка получения суммарных остатков: %s", e, exc_info=True)
            return {}

    # ------------------------------------------------------------------
    # FBO — склад Wildberries
    # ------------------------------------------------------------------

    def get_fbo_stocks(self, use_cache: bool = True, force_refresh: bool = False) -> List[Dict]:
        """
        Получить остатки FBO (склад Wildberries) через Statistics API.

        Args:
            use_cache: Использовать кеш если доступен
            force_refresh: Принудительно обновить данные (игнорировать кеш)

        Returns:
            Список остатков с полями nmId, supplierArticle, quantity, warehouseName, …
        """
        cache_key = "fbo_stocks"

        if not force_refresh and use_cache:
            cached = self._cache.get(cache_key)
            if cached is not None:
                logger.debug("Возвращаем кешированные FBO остатки (%d записей)", len(cached))
                return cached

        try:
            logger.debug("Загружаем FBO остатки через Statistics API...")
            stocks = self._get_fbo_stocks_statistics()

            if stocks:
                self._cache.set(cache_key, stocks)
                return stocks
            else:
                logger.warning("Statistics API вернул пустой результат, пробуем fallback...")

        except Exception as e:
            logger.warning("Statistics API failed: %s", e)

        try:
            logger.debug("Fallback на Analytics API...")
            stocks = self._get_fbo_stocks_analytics_fallback()

            if stocks:
                self._cache.set(cache_key, stocks)
                return stocks
        except Exception as e:
            logger.error("Оба метода получения FBO остатков не сработали: %s", e)

        return []

    def _get_fbo_stocks_statistics(self) -> List[Dict]:
        """
        Внутренний метод: Получение остатков через Statistics API.
        Rate limit: 1 запрос/минута.
        """
        all_stocks = []
        date_from = "2019-06-20T00:00:00"
        iteration = 0
        max_iterations = 100

        while iteration < max_iterations:
            iteration += 1
            logger.debug("Statistics API запрос #%d, dateFrom=%s", iteration, date_from)

            try:
                response = self.api.get(
                    "/api/v1/supplier/stocks",
                    params={"dateFrom": date_from},
                    base_url=self.api.config.statistics_url
                )

                if not isinstance(response, list):
                    logger.warning("Statistics API вернул не-list: %s", type(response))
                    break

                if not response:
                    logger.debug("Получен пустой массив, все остатки выгружены")
                    break

                batch_size = len(response)
                all_stocks.extend(response)
                logger.debug("Получено %d записей в батче", batch_size)

                last_record = response[-1]
                last_change = last_record.get('lastChangeDate')

                if not last_change or last_change == date_from:
                    logger.debug("Нет lastChangeDate для пагинации, завершаем")
                    break

                date_from = last_change

                if iteration > 1 and iteration < max_iterations:
                    time_module.sleep(0.5)

            except Exception as e:
                logger.error("Ошибка в Statistics API: %s", e)
                break

        logger.info("Всего получено %d записей через Statistics API", len(all_stocks))
        return all_stocks

    def _get_fbo_stocks_analytics_fallback(self) -> List[Dict]:
        """
        Fallback метод: Получение остатков через Analytics API + Content API.
        """
        try:
            logger.debug("Начинаем загрузку FBO через Analytics API + Content API (fallback)")

            nm_to_article = {}
            cursor = {"limit": 100}

            while True:
                response = self.api.post(
                    "/content/v2/get/cards/list",
                    data={
                        "settings": {
                            "cursor": cursor,
                            "filter": {"withPhoto": -1}
                        }
                    },
                    base_url=API_ENDPOINTS["content"]
                )

                if not isinstance(response, dict):
                    break

                cards = response.get('cards', [])
                if not cards:
                    break

                for card in cards:
                    nm_id = card.get('nmID')
                    if nm_id:
                        nm_to_article[nm_id] = card.get('vendorCode', '')

                response_cursor = response.get('cursor', {})
                total = response_cursor.get('total', 0)

                if len(cards) < 100 or len(nm_to_article) >= total:
                    break

                last_card = cards[-1]
                cursor = {
                    "limit": 100,
                    "updatedAt": last_card.get('updatedAt'),
                    "nmID": last_card.get('nmID')
                }

            logger.debug("Загружено %d товаров из Content API", len(nm_to_article))

            today = datetime.now().strftime("%Y-%m-%d")

            response = self.api.post(
                "/api/v2/stocks-report/products/groups",
                data={
                    "nmIDs": [],
                    "subjectIDs": [],
                    "brandNames": [],
                    "tagIDs": [],
                    "currentPeriod": {
                        "start": today,
                        "end": today
                    },
                    "stockType": "wb",
                    "skipDeletedNm": True,
                    "availabilityFilters": [],
                    "orderBy": {
                        "field": "avgOrders",
                        "mode": "asc"
                    },
                    "limit": 1000,
                    "offset": 0
                },
                base_url=API_ENDPOINTS["analytics"]
            )

            result = []
            if isinstance(response, dict) and 'data' in response:
                data = response['data']
                groups = data.get('groups', [])

                logger.debug("Получено %d групп из Analytics API", len(groups))

                for group in groups:
                    nm_id = group.get('nmID')
                    stocks = group.get('stocks', [])
                    total_stock = sum(s.get('stock', 0) for s in stocks)
                    supplier_article = nm_to_article.get(nm_id, '')

                    result.append({
                        'nmId': nm_id,
                        'supplierArticle': supplier_article,
                        'stockCount': total_stock,
                        'stocks': stocks
                    })

            logger.info("Fallback: сформировано %d записей", len(result))
            return result

        except Exception as e:
            logger.error("Ошибка fallback метода: %s", e, exc_info=True)
            return []

    def clear_fbo_cache(self):
        """Очистить кеш FBO остатков"""
        self._cache.clear()
        logger.info("Кеш FBO остатков очищен")

    def get_fbo_stocks_by_warehouse(self, stocks: List[Dict]) -> Dict[str, List[Dict]]:
        """
        Группирует остатки FBO по складам.

        Args:
            stocks: Список остатков из get_fbo_stocks()

        Returns:
            Словарь {warehouse_name: [stocks]}
        """
        by_warehouse = {}
        for stock in stocks:
            warehouse = stock.get('warehouseName', 'Неизвестно')
            if warehouse not in by_warehouse:
                by_warehouse[warehouse] = []
            by_warehouse[warehouse].append(stock)
        return by_warehouse

    def export_fbo_stocks_to_csv(self, stocks: List[Dict], format_type: str = "full") -> str:
        """
        Экспорт остатков FBO в CSV.

        Args:
            stocks: Список остатков
            format_type: "full" (все поля) или "simple" (основные поля)

        Returns:
            CSV строка
        """
        import csv
        import io

        output = io.StringIO()

        if format_type == "simple":
            fieldnames = ['supplierArticle', 'nmId', 'quantity', 'warehouseName', 'brand', 'subject']
            writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()

            for stock in stocks:
                writer.writerow({
                    'supplierArticle': stock.get('supplierArticle', ''),
                    'nmId': stock.get('nmId', ''),
                    'quantity': stock.get('quantity', 0),
                    'warehouseName': stock.get('warehouseName', ''),
                    'brand': stock.get('brand', ''),
                    'subject': stock.get('subject', '')
                })
        else:
            fieldnames = [
                'supplierArticle', 'nmId', 'barcode', 'quantity', 'quantityFull',
                'inWayToClient', 'inWayFromClient', 'warehouseName',
                'category', 'subject', 'brand', 'techSize',
                'Price', 'Discount', 'lastChangeDate'
            ]
            writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()

            for stock in stocks:
                writer.writerow(stock)

        return output.getvalue()

    # === УСТАРЕВШИЕ МЕТОДЫ (оставлены для обратной совместимости) ===

    def get_fbo_stocks_with_article(self) -> List[Dict]:
        """[DEPRECATED] Используйте get_fbo_stocks() напрямую."""
        return self.get_fbo_stocks()

    def get_fbo_stocks_detailed(self) -> List[Dict]:
        """[DEPRECATED] Используйте get_fbo_stocks() напрямую."""
        return self.get_fbo_stocks()
