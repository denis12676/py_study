"""
Реестр методов Ozon API

Каталог методов Ozon Seller API для автоматического выбора ИИ-агентом.
"""

from typing import List, Dict, Any

class OzonMethodRegistry:
    """
    Реестр всех методов Ozon API.
    """
    
    METHODS: List[Dict[str, Any]] = [
        # ==========================================
        # ТОВАРЫ (Products)
        # ==========================================
        {
            "name": "get_product_list",
            "description": "Получение списка идентификаторов товаров",
            "endpoint": "/v2/product/list",
            "method": "POST",
            "category": "products",
            "params": {
                "filter": {"visibility": "string"},
                "limit": "int",
                "last_id": "string"
            },
            "use_cases": ["Получение списка всех товаров", "Пагинация каталога"]
        },
        {
            "name": "get_product_info",
            "description": "Получение детальной информации о товаре",
            "endpoint": "/v2/product/info",
            "method": "POST",
            "category": "products",
            "params": {"product_id": "int", "sku": "int"},
            "use_cases": ["Просмотр характеристик товара", "Проверка статуса модерации"]
        },
        {
            "name": "get_product_info_list",
            "description": "Получение информации по списку товаров (макс 1000)",
            "endpoint": "/v2/product/info/list",
            "method": "POST",
            "category": "products",
            "params": {"product_id": "array", "sku": "array"},
            "use_cases": ["Массовое получение данных о товарах"]
        },
        
        # ==========================================
        # ЦЕНЫ (Prices)
        # ==========================================
        {
            "name": "update_prices",
            "description": "Обновление цен на товары",
            "endpoint": "/v1/product/import/prices",
            "method": "POST",
            "category": "prices",
            "params": {
                "prices": "array - список объектов с product_id, price, old_price"
            },
            "use_cases": ["Изменение цен", "Установка скидок"]
        },
        {
            "name": "get_product_prices",
            "description": "Получение информации о ценах",
            "endpoint": "/v4/product/info/prices",
            "method": "POST",
            "category": "prices",
            "params": {"filter": "object", "limit": "int"},
            "use_cases": ["Просмотр текущих цен и акций"]
        },

        # ==========================================
        # ОСТАТКИ (Stocks)
        # ==========================================
        {
            "name": "get_product_stocks",
            "description": "Получение информации об остатках на складах",
            "endpoint": "/v3/product/info/stocks",
            "method": "POST",
            "category": "stocks",
            "params": {"filter": "object", "limit": "int"},
            "use_cases": ["Проверка остатков FBS и FBO"]
        },
        {
            "name": "update_stocks",
            "description": "Обновление остатков на складах (FBS)",
            "endpoint": "/v1/product/import/stocks",
            "method": "POST",
            "category": "stocks",
            "params": {
                "stocks": "array - список объектов с product_id, stock"
            },
            "use_cases": ["Синхронизация остатков со своего склада"]
        },

        # ==========================================
        # ЗАКАЗЫ (Orders)
        # ==========================================
        {
            "name": "get_fbs_unfulfilled_orders",
            "description": "Получение списка невыполненных заказов (FBS)",
            "endpoint": "/v3/posting/fbs/unfulfilled/list",
            "method": "POST",
            "category": "orders",
            "params": {"filter": "object", "limit": "int"},
            "use_cases": ["Сбор новых заказов для упаковки"]
        },
        {
            "name": "get_fbo_orders",
            "description": "Получение списка заказов со склада Ozon (FBO)",
            "endpoint": "/v2/posting/fbo/list",
            "method": "POST",
            "category": "orders",
            "params": {"filter": "object", "limit": "int"},
            "use_cases": ["Анализ продаж FBO"]
        },

        # ==========================================
        # АНАЛИТИКА (Analytics)
        # ==========================================
        {
            "name": "get_analytics_data",
            "description": "Получение аналитических данных (метрики продаж)",
            "endpoint": "/v1/analytics/data",
            "method": "POST",
            "category": "analytics",
            "params": {
                "date_from": "string",
                "date_to": "string",
                "metrics": "array",
                "dimension": "array"
            },
            "use_cases": ["Анализ воронки продаж", "Выручка за период"]
        },
        {
            "name": "get_stock_on_warehouses",
            "description": "Отчет об остатках на складах Ozon",
            "endpoint": "/v1/analytics/stock_on_warehouses",
            "method": "POST",
            "category": "analytics",
            "params": {},
            "use_cases": ["Проверка наличия товаров на региональных складах"]
        },
    ]

    @classmethod
    def find_method(cls, query: str) -> List[Dict[str, Any]]:
        query_lower = query.lower()
        matching_methods = []
        for method in cls.METHODS:
            score = 0
            if any(word in method["description"].lower() for word in query_lower.split()):
                score += 2
            if any(word in method["name"].lower() for word in query_lower.split()):
                score += 1
            if score > 0:
                matching_methods.append((score, method))
        matching_methods.sort(key=lambda x: x[0], reverse=True)
        return [method for score, method in matching_methods[:5]]
