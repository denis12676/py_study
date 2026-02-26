"""
ИИ-агент для Wildberries API

Этот агент автоматически определяет какой метод API нужно вызвать
на основе запроса пользователя и выполняет его.
"""

import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from wb_client import WildberriesAPI, WBConfig, API_ENDPOINTS
from managers import ProductsManager, InventoryManager, AnalyticsManager, OrdersManager, AdvertisingManager
from api_registry import WBMethodRegistry
from nlp_engine import RequestAnalyzer
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class WildberriesAIAgent:
    """ИИ-агент для автоматизации работы с Wildberries API."""
    
    def __init__(self, api_token: str):
        config = WBConfig(api_token=api_token)
        self.api = WildberriesAPI(config)
        
        # Инициализируем менеджеры
        self.products = ProductsManager(self.api)
        self.inventory = InventoryManager(self.api)
        self.analytics = AnalyticsManager(self.api)
        self.orders = OrdersManager(self.api)
        self.advertising = AdvertisingManager(self.api)

        self._analyzer = RequestAnalyzer()
        self.last_result: Any = None
        self._test_connection()
    
    def _test_connection(self):
        try:
            self.api.get("/api/v1/seller-info", base_url=API_ENDPOINTS["tariffs"])
        except: pass
    
    def execute(self, query: str) -> Any:
        logger.info("Запрос: %s", query)
        action_info = self._analyzer.analyze(query)
        action = action_info["action"]
        params = self._extract_params(query, action)
        
        try:
            result = self._execute_action(action, params)
            self.last_result = result
            self._print_result(action, result, params)
            return result
        except Exception as e:
            logger.error("Ошибка выполнения: %s", e)
            return None

    def _execute_action(self, action: str, params: Dict[str, Any]) -> Any:
        if action == "list_products":
            return self.products.get_all_products(limit=params.get("limit", 100))
        elif action == "search_products":
            return self.products.search_products(query=params.get("query", ""), limit=params.get("limit", 100))
        elif action == "update_price":
            return self.products.update_price(nm_id=params["nm_id"], price=params["price"], discount=params.get("discount"))
        elif action == "revenue_report":
            return self.analytics.calculate_revenue(days=params.get("days", 30))
        elif action == "top_products":
            return self.analytics.get_top_products(days=params.get("days", 30), limit=params.get("limit", 10))
        elif action == "check_stocks":
            warehouses = self.inventory.get_warehouses()
            if warehouses:
                return self.inventory.get_stocks(warehouse_id=warehouses[0]["id"])
            return []
        # Fallback to general API help
        return {"error": f"Action {action} not fully implemented in agent yet"}

    def _extract_params(self, query: str, action: str) -> Dict[str, Any]:
        import re
        params = {}
        query_lower = query.lower()
        numbers = re.findall(r'\d+', query)
        
        if action == "update_price" and len(numbers) >= 2:
            params["nm_id"] = int(numbers[0])
            params["price"] = float(numbers[1])
        elif action == "search_products":
            params["query"] = query.split()[-1]
        else:
            params["days"] = 30
            params["limit"] = 10
        return params

    def _print_result(self, action: str, result: Any, params: Dict[str, Any]):
        if not result:
            logger.info("Результат пуст")
            return

        if isinstance(result, list):
            logger.info("Найдено %d записей", len(result))
            for i, item in enumerate(result[:5], 1):
                # Handle both Pydantic models and dicts
                if isinstance(item, BaseModel):
                    logger.info("%d. %s", i, item.model_dump_json())
                else:
                    logger.info("%d. %s", i, item)
        elif isinstance(result, BaseModel):
            logger.info("Результат: %s", result.model_dump_json(indent=2))
        else:
            logger.info("Результат: %s", result)
