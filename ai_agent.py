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

logger = logging.getLogger(__name__)


class WildberriesAIAgent:
    """
    ИИ-агент для автоматизации работы с Wildberries API.
    
    Примеры использования:
    
    # Создание агента
    agent = WildberriesAIAgent("ваш_api_токен")
    
    # Простые запросы
    agent.execute("Покажи все мои товары")
    agent.execute("Какая выручка за последние 30 дней?")
    agent.execute("Выведи топ 5 продаваемых товаров")
    agent.execute("Запусти рекламную кампанию 12345")
    
    # Запросы с параметрами
    agent.execute("Обнови цену товара 12345 на 1500 рублей")
    agent.execute("Получи отзывы за последнюю неделю")
    """
    
    def __init__(self, api_token: str):
        """
        Инициализация агента
        
        Args:
            api_token: API токен от Wildberries (получить можно в личном кабинете)
        """
        config = WBConfig(api_token=api_token)
        self.api = WildberriesAPI(config)
        
        # Инициализируем менеджеры
        self.products = ProductsManager(self.api)
        self.inventory = InventoryManager(self.api)
        self.analytics = AnalyticsManager(self.api)
        self.orders = OrdersManager(self.api)
        self.advertising = AdvertisingManager(self.api)

        # NLP-анализатор запросов
        self._analyzer = RequestAnalyzer()

        # Последний результат
        self.last_result: Any = None

        # Тестируем соединение
        self._test_connection()

        logger.info("Агент Wildberries инициализирован. Базовый URL: %s", config.base_url)
    
    def _test_connection(self):
        """Тестирование соединения с API"""
        try:
            self.api.get("/api/v1/seller-info", base_url=API_ENDPOINTS["tariffs"])
        except Exception as e:
            logger.warning("Не удалось проверить соединение: %s. Это может быть временная проблема с серверами WB", e)
    
    def _analyze_request(self, query: str) -> Dict[str, Any]:
        """
        Анализирует запрос и определяет какое действие выполнить.

        Args:
            query: Запрос на естественном языке

        Returns:
            Словарь с информацией о действии
        """
        return self._analyzer.analyze(query)
    
    def _extract_params(self, query: str, action: str) -> Dict[str, Any]:
        """
        Извлекает параметры из запроса
        """
        params = {}
        query_lower = query.lower()
        
        # Извлекаем числа (ID, цены, количества)
        import re
        numbers = re.findall(r'\d+', query)
        
        if action == "update_price":
            # Ищем артикул и цену
            if len(numbers) >= 2:
                params["nm_id"] = int(numbers[0])
                params["price"] = float(numbers[1])
            # Ищем скидку
            if "скидка" in query_lower or "%" in query:
                discount_match = re.search(r'(\d+)%', query)
                if discount_match:
                    params["discount"] = int(discount_match.group(1))
        
        elif action == "search_products":
            # Ищем поисковый запрос
            if "найди" in query_lower:
                match = re.search(r'найди\s+(.+?)(?:\s+в\s+|$)', query_lower)
                if match:
                    params["query"] = match.group(1).strip()
            else:
                params["query"] = " ".join(query.split()[-3:])  # Последние 3 слова
        
        elif action in ["start_campaign", "pause_campaign", "delete_campaign", "campaign_stats", "update_bid"]:
            # Ищем ID кампании
            if numbers:
                params["campaign_id"] = int(numbers[0])
        
        elif action == "update_bid":
            # Ищем новую ставку
            if len(numbers) >= 2:
                params["bid"] = int(numbers[-1])
        
        elif action in ["sales_report", "orders_report", "top_products", "revenue_report"]:
            # Ищем конкретную дату (форматы: 23.02.2026, 23.02.26, 23/02/2026)
            date_match = re.search(r'(\d{1,2})[./](\d{1,2})[./](\d{2,4})', query)
            if date_match:
                day, month, year = date_match.groups()
                # Формируем дату в формате YYYY-MM-DD
                if len(year) == 2:
                    year = '20' + year  # Предполагаем 21 век
                params["date_from"] = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
                params["days"] = 1  # Для конкретной даты берем 1 день
            else:
                # Ищем период если даты нет
                if "недел" in query_lower or "7" in query:
                    params["days"] = 7
                elif "месяц" in query_lower or "30" in query:
                    params["days"] = 30
                elif "год" in query_lower or "365" in query:
                    params["days"] = 365
                else:
                    params["days"] = 30
            
            # Ищем лимит для топа
            if "топ" in query_lower and numbers:
                params["limit"] = int(numbers[0])
            else:
                params["limit"] = 10
        
        return params
    
    def execute(self, query: str) -> Any:
        """
        Выполняет запрос пользователя
        
        Args:
            query: Запрос на естественном языке
            
        Returns:
            Результат выполнения операции
        """
        logger.info("Запрос: %s", query)

        # Анализируем запрос
        action_info = self._analyze_request(query)
        action = action_info["action"]
        category = action_info["type"]

        # Извлекаем параметры
        params = self._extract_params(query, action)

        logger.info("Действие: %s | Категория: %s", action, category)
        if params:
            logger.debug("Параметры: %s", params)
        
        try:
            # Выполняем действие
            result = self._execute_action(action, params)
            self.last_result = result
            
            # Красивый вывод результата
            self._print_result(action, result, params)
            
            return result
            
        except Exception as e:
            logger.error("Ошибка: %s", e)
            return None
    
    def _execute_action(self, action: str, params: Dict[str, Any]) -> Any:
        """Выполняет конкретное действие"""
        
        # PRODUCTS
        if action == "list_products":
            return self.products.get_all_products(limit=params.get("limit", 100))
        
        elif action == "search_products":
            return self.products.search_products(
                query=params.get("query", ""),
                limit=params.get("limit", 100)
            )
        
        elif action == "update_price":
            if "nm_id" not in params or "price" not in params:
                raise ValueError("Укажите артикул товара и новую цену")
            return self.products.update_price(
                nm_id=params["nm_id"],
                price=params["price"],
                discount=params.get("discount")
            )
        
        elif action == "check_stocks":
            warehouses = self.inventory.get_warehouses()
            if warehouses:
                return self.inventory.get_stocks(warehouse_id=warehouses[0]["id"])
            return []
        
        # ANALYTICS
        elif action == "sales_report":
            return self.analytics.get_sales(
                date_from=None,
                date_to=None,
                limit=params.get("limit", 1000)
            )
        
        elif action == "orders_report":
            return self.analytics.get_orders(
                date_from=None,
                date_to=None,
                limit=params.get("limit", 1000)
            )
        
        elif action == "revenue_report":
            # Если указана конкретная дата, используем её
            if "date_from" in params:
                sales = self.analytics.get_sales(date_from=params["date_from"])
                from datetime import datetime, timedelta
                # Рассчитываем выручку для конкретного дня
                total_revenue = sum(float(sale.get("forPay", 0) or 0) for sale in sales if not sale.get("isCancel", False))
                total_sales = len([s for s in sales if not s.get("isCancel", False)])
                avg_check = total_revenue / total_sales if total_sales > 0 else 0
                return {
                    "date": params["date_from"],
                    "total_revenue": round(total_revenue, 2),
                    "total_sales": total_sales,
                    "average_check": round(avg_check, 2)
                }
            else:
                # Используем стандартный расчет за период
                return self.analytics.calculate_revenue(days=params.get("days", 30))
        
        elif action == "top_products":
            return self.analytics.get_top_products(
                days=params.get("days", 30),
                limit=params.get("limit", 10)
            )
        
        elif action == "detailed_report":
            return self.analytics.get_detailed_report(
                date_from=None,
                date_to=None,
                limit=params.get("limit", 1000)
            )
        
        elif action == "weekly_report":
            return self.analytics.get_weekly_sales_report(
                week_start=params.get("week_start")
            )
        
        elif action == "stocks_report":
            return self.analytics.get_stocks_report()
        
        # ADVERTISING
        elif action == "list_campaigns":
            return self.advertising.get_campaigns()
        
        elif action == "campaign_stats":
            if "campaign_id" not in params:
                raise ValueError("Укажите ID кампании")
            return self.advertising.get_campaign_stats([params["campaign_id"]])
        
        elif action == "start_campaign":
            if "campaign_id" not in params:
                raise ValueError("Укажите ID кампании")
            success = self.advertising.start_campaign(params["campaign_id"])
            return {"success": success, "action": "start_campaign", "campaign_id": params["campaign_id"]}
        
        elif action == "pause_campaign":
            if "campaign_id" not in params:
                raise ValueError("Укажите ID кампании")
            success = self.advertising.pause_campaign(params["campaign_id"])
            return {"success": success, "action": "pause_campaign", "campaign_id": params["campaign_id"]}
        
        elif action == "delete_campaign":
            if "campaign_id" not in params:
                raise ValueError("Укажите ID кампании")
            success = self.advertising.delete_campaign(params["campaign_id"])
            return {"success": success, "action": "delete_campaign", "campaign_id": params["campaign_id"]}
        
        elif action == "update_bid":
            if "campaign_id" not in params or "bid" not in params:
                raise ValueError("Укажите ID кампании и новую ставку")
            success = self.advertising.update_bid([params["campaign_id"]], params["bid"])
            return {"success": success, "action": "update_bid", "campaign_id": params["campaign_id"], "bid": params["bid"]}
        
        # ORDERS
        elif action == "new_orders":
            return self.orders.get_new_orders(limit=params.get("limit", 100))
        
        # GENERAL
        elif action == "seller_info":
            return self.api.get("/api/v1/seller-info", base_url=self.api.config.base_url)
        
        elif action == "help":
            return self.get_help()
        
        else:
            return {"error": f"Неизвестное действие: {action}"}
    
    def _print_result(self, action: str, result: Any, params: Dict[str, Any]):
        """Красиво выводит результат"""

        if isinstance(result, list):
            if len(result) == 0:
                logger.info("Нет данных для отображения")
                return

            logger.info("Найдено %d записей:", len(result))

            if action in ["list_products", "search_products"]:
                for i, item in enumerate(result[:10], 1):
                    nm_id = item.get("nmID", "N/A")
                    name = item.get("title", "Без названия")
                    price = item.get("sizes", [{}])[0].get("price", 0)
                    discount = item.get("discount", 0)
                    logger.info("%d. Артикул: %s | %s | Цена: %s₽ (скидка %s%%)", i, nm_id, name, price, discount)

                if len(result) > 10:
                    logger.info("... и еще %d товаров", len(result) - 10)

            elif action == "top_products":
                for i, item in enumerate(result, 1):
                    logger.info("%d. %s (арт. %s) | Продано: %s шт. | Выручка: %.2f₽",
                                i, item['name'], item['nm_id'], item['quantity'], item['revenue'])

            elif action == "sales_report":
                total_revenue = sum(float(sale.get("totalPrice", 0)) for sale in result)
                logger.info("Общая выручка: %.2f₽ | Продаж: %d", total_revenue, len(result))
                for sale in result[:5]:
                    logger.info("  - %s | %s₽ | %s",
                                sale.get('supplierArticle', 'N/A'), sale.get('totalPrice', 0), sale.get('date', 'N/A'))

            elif action == "list_campaigns":
                for i, campaign in enumerate(result, 1):
                    status = campaign.get("status", 0)
                    status_text = {4: "Готова", 7: "Активна", 11: "Пауза"}.get(status, "Другой")
                    logger.info("%d. ID: %s | %s | Статус: %s | Тип: %s",
                                i, campaign.get('advertId'), campaign.get('name', 'Без названия'),
                                status_text, campaign.get('type', 'N/A'))

            else:
                logger.info("Результат: %s", json.dumps(result[:5], indent=2, ensure_ascii=False))
                if len(result) > 5:
                    logger.info("... и еще %d записей", len(result) - 5)

        elif isinstance(result, dict):
            if "error" in result:
                logger.error("Ошибка: %s", result['error'])
            elif "success" in result:
                status = "Успешно" if result["success"] else "Не удалось"
                logger.info("%s: %s", status, result.get('action', 'операция'))
                if "campaign_id" in result:
                    logger.info("Кампания ID: %s", result['campaign_id'])
            elif "date" in result and "total_revenue" in result:
                logger.info("ВЫРУЧКА ЗА %s: %.2f ₽ | Продаж: %d | Средний чек: %.2f ₽",
                            result['date'], result['total_revenue'], result['total_sales'], result['average_check'])
            elif "week_start" in result:
                logger.info("ЕЖЕНЕДЕЛЬНЫЙ ОТЧЕТ: %s - %s | Выручка: %.2f ₽ | Продаж: %d | Возвратов: %d (%.1f%%)",
                            result['week_start'], result['week_end'],
                            result['total_revenue'], result['total_sales'],
                            result['total_returns'], result['return_rate'])

                if result.get('daily_breakdown'):
                    for day in result['daily_breakdown'][:7]:
                        logger.info("%s: %.2f ₽ | Продаж: %d | Возвратов: %d",
                                    day['date'], day['revenue'], day['sales_count'], day['returns_count'])

                if result.get('top_products'):
                    for i, product in enumerate(result['top_products'][:10], 1):
                        logger.info("%d. %s | %s | Арт. %s | Выручка: %.2f ₽ | Продаж: %s",
                                    i, product['subject'], product['brand'], product['nmId'],
                                    product['revenue'], product['quantity'])

                if result.get('category_breakdown'):
                    for cat in result['category_breakdown'][:5]:
                        logger.info("%s: %.2f ₽ (%d продаж)", cat['category'], cat['revenue'], cat['sales'])
            else:
                logger.info("Результат: %s", json.dumps(result, indent=2, ensure_ascii=False))

        else:
            logger.info("Результат: %s", result)
    
    def get_help(self) -> str:
        """Возвращает справку по использованию"""
        help_text = """
🤖 Wildberries AI Agent - справка

Доступные команды:

📦 ТОВАРЫ:
  "Покажи все товары" - вывести каталог
  "Найди товар [название]" - поиск товара
  "Обнови цену [артикул] на [цена]" - изменить цену
  "Проверь остатки" - текущие остатки на складах

📊 АНАЛИТИКА:
  "Выручка за 30 дней" - отчет по продажам
  "Топ 10 товаров" - лучшие продажи
  "Продажи за неделю" - отчет за 7 дней
  "Еженедельный отчет" - детальный отчет по неделям
  "Детальный отчет" - финансовый отчет с комиссиями

📢 РЕКЛАМА:
  "Покажи рекламные кампании" - список кампаний
  "Запусти кампанию [ID]" - запуск рекламы
  "Останови кампанию [ID]" - пауза
  "Измени ставку [ID] на [ставка]" - обновление CPC

📦 ЗАКАЗЫ:
  "Новые заказы" - заказы для сборки

👤 ИНФОРМАЦИЯ:
  "Информация о магазине" - данные продавца

Примеры:
  agent.execute("Покажи все мои товары")
  agent.execute("Какая выручка за последние 30 дней?")
  agent.execute("Запусти рекламную кампанию 12345")
        """
        logger.info(help_text)
        return help_text

    def suggest_method(self, description: str) -> List[Dict[str, Any]]:
        """
        Предлагает методы API подходящие под описание задачи

        Args:
            description: Описание задачи

        Returns:
            Список подходящих методов
        """
        methods = WBMethodRegistry.find_method(description)

        logger.info("Для задачи \"%s\" найдены методы:", description)
        for i, method in enumerate(methods, 1):
            logger.info("%d. %s — %s | Endpoint: %s %s | Категория: %s",
                        i, method['name'], method['description'],
                        method['method'], method['endpoint'], method['category'])

        return methods
