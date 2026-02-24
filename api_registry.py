"""
Реестр методов Wildberries API

Этот файл содержит полный каталог всех доступных методов API с описаниями,
чтобы ИИ-агент мог автоматически выбирать нужный метод на основе запроса пользователя.

Каждый метод содержит:
- name: Название метода
- description: Описание что делает метод
- endpoint: URL endpoint
- method: HTTP метод (GET, POST, PUT, DELETE, PATCH)
- category: Категория API (для определения base_url)
- params: Описание параметров
- response: Описание ответа
- use_cases: Примеры использования
"""

from typing import List, Dict, Any


class WBMethodRegistry:
    """
    Реестр всех методов Wildberries API.
    Используется ИИ-агентом для автоматического выбора метода.
    """
    
    METHODS: List[Dict[str, Any]] = [
        # ==========================================
        # ОБЩИЕ МЕТОДЫ (General)
        # ==========================================
        {
            "name": "check_connection",
            "description": "Проверка подключения к API и валидности токена",
            "endpoint": "/ping",
            "method": "GET",
            "category": "statistics",
            "params": {},
            "response": {"status": "string"},
            "use_cases": ["Проверка работоспособности API", "Валидация токена"]
        },
        {
            "name": "get_seller_info",
            "description": "Получение информации о продавце (название, ID, тарифы)",
            "endpoint": "/api/v1/seller-info",
            "method": "GET",
            "category": "statistics",
            "params": {},
            "response": {
                "id": "int - ID продавца",
                "name": "string - Название продавца",
                "registration_date": "string - Дата регистрации"
            },
            "use_cases": ["Получение данных о магазине", "Проверка авторизации"]
        },
        {
            "name": "get_seller_news",
            "description": "Получение новостей портала продавцов",
            "endpoint": "/api/communications/v2/news",
            "method": "GET",
            "category": "statistics",
            "params": {},
            "response": {"news": "array - список новостей"},
            "use_cases": ["Мониторинг обновлений WB", "Получение важных уведомлений"]
        },
        
        # ==========================================
        # КОНТЕНТ И ТОВАРЫ (Content)
        # ==========================================
        {
            "name": "get_product_categories",
            "description": "Получение списка всех категорий товаров",
            "endpoint": "/content/v2/object/parent/all",
            "method": "GET",
            "category": "content",
            "params": {},
            "response": {
                "data": "array - список категорий с id и name"
            },
            "use_cases": ["Построение дерева категорий", "Анализ рынка по категориям"]
        },
        {
            "name": "get_product_subjects",
            "description": "Получение списка всех предметов (подкатегорий)",
            "endpoint": "/content/v2/object/all",
            "method": "GET",
            "category": "content",
            "params": {},
            "response": {
                "data": "array - список предметов с subjectID и subjectName"
            },
            "use_cases": ["Поиск предмета для создания карточки", "Анализ ниши"]
        },
        {
            "name": "get_products_list",
            "description": "Получение списка товаров продавца (актуальный метод v2)",
            "endpoint": "/content/v2/get/cards/list",
            "method": "POST",
            "category": "content",
            "params": {
                "settings": {
                    "cursor": {"limit": "int - лимит записей"},
                    "filter": {"withPhoto": "int -1/0/1", "textSearch": "string - поисковый запрос"}
                }
            },
            "response": {
                "cards": "array - список карточек товаров",
                "cursor": {"total": "int - всего записей"}
            },
            "use_cases": [
                "Получение каталога товаров",
                "Поиск товаров по названию/артикулу",
                "Выгрузка всех карточек"
            ]
        },
        {
            "name": "get_products_with_prices",
            "description": "Получение товаров с ценами и скидками (Prices API)",
            "endpoint": "/api/v2/list/goods/filter",
            "method": "GET",
            "category": "prices",
            "params": {
                "limit": "int - лимит (макс 1000)",
                "offset": "int - смещение",
                "search": "string - поисковый запрос (опционально)"
            },
            "response": {
                "data": {
                    "listGoods": "array - товары с ценами и скидками"
                }
            },
            "use_cases": [
                "Выгрузка всех товаров для анализа",
                "Поиск товаров по артикулу",
                "Фильтрация по ценовым диапазонам"
            ]
        },
        {
            "name": "get_quarantine_products",
            "description": "Получение товаров в карантине (цены не обновлены более 30 дней)",
            "endpoint": "/api/v2/quarantine/goods",
            "method": "GET",
            "category": "content",
            "params": {},
            "response": {
                "data": "array - товары в карантине с причинами"
            },
            "use_cases": [
                "Проверка товаров в карантине",
                "Обновление устаревших цен"
            ]
        },
        {
            "name": "update_prices",
            "description": "Обновление цен на товары",
            "endpoint": "/api/v2/upload/task",
            "method": "POST",
            "category": "content",
            "params": {
                "data": "array - массив объектов с nmID, price, discount"
            },
            "response": {
                "uploadID": "int - ID задачи на обновление"
            },
            "use_cases": [
                "Массовое обновление цен",
                "Установка скидок",
                "Автоматическое ценообразование"
            ]
        },
        {
            "name": "update_sizes_prices",
            "description": "Обновление цен для конкретных размеров товара",
            "endpoint": "/api/v2/upload/task/size",
            "method": "POST",
            "category": "content",
            "params": {
                "data": "array - массив с размерами и ценами"
            },
            "response": {
                "uploadID": "int - ID задачи"
            },
            "use_cases": [
                "Разные цены для разных размеров",
                "Управление ценами по SKU"
            ]
        },
        {
            "name": "get_upload_status",
            "description": "Проверка статуса загрузки/обновления товаров",
            "endpoint": "/api/v2/buffer/tasks",
            "method": "GET",
            "category": "content",
            "params": {},
            "response": {
                "data": "array - статусы загрузок"
            },
            "use_cases": [
                "Проверка завершения обновления цен",
                "Мониторинг ошибок загрузки"
            ]
        },
        
        # ==========================================
        # СКЛАДЫ И ОСТАТКИ (Warehouses & Stocks)
        # ==========================================
        {
            "name": "get_warehouses",
            "description": "Получение списка складов продавца",
            "endpoint": "/api/v3/warehouses",
            "method": "GET",
            "category": "content",
            "params": {},
            "response": {
                "data": "array - склады с ID, названием, адресом"
            },
            "use_cases": [
                "Управление складами",
                "Проверка доступных складов"
            ]
        },
        {
            "name": "create_warehouse",
            "description": "Создание нового склада",
            "endpoint": "/api/v3/warehouses",
            "method": "POST",
            "category": "content",
            "params": {
                "name": "string - название склада",
                "address": "string - адрес"
            },
            "response": {"warehouseID": "int - ID созданного склада"},
            "use_cases": ["Добавление нового склада", "Расширение сети складов"]
        },
        {
            "name": "get_stocks",
            "description": "Получение остатков на складах",
            "endpoint": "/api/v3/stocks/{warehouseId}",
            "method": "POST",
            "category": "content",
            "params": {
                "warehouseId": "int - ID склада (в URL)",
                "skus": "array - список баркодов для фильтрации"
            },
            "response": {
                "stocks": "array - остатки по товарам"
            },
            "use_cases": [
                "Проверка остатков",
                "Управление запасами",
                "Анализ товаров на исходе"
            ]
        },
        {
            "name": "update_stocks",
            "description": "Обновление остатков на складе",
            "endpoint": "/api/v3/stocks/{warehouseId}",
            "method": "PUT",
            "category": "content",
            "params": {
                "warehouseId": "int - ID склада (в URL)",
                "stocks": "array - массив с баркодом и количеством"
            },
            "response": {},
            "use_cases": [
                "Обновление остатков после поставки",
                "Синхронизация с учетной системой"
            ]
        },
        
        # ==========================================
        # СТАТИСТИКА И АНАЛИТИКА (Statistics)
        # ==========================================
        {
            "name": "get_sales_report",
            "description": "Получение отчета о продажах (детальная статистика)",
            "endpoint": "/api/v1/supplier/sales",
            "method": "GET",
            "category": "statistics",
            "params": {
                "dateFrom": "string - дата начала (YYYY-MM-DD)",
                "dateTo": "string - дата окончания (YYYY-MM-DD)",
                "rrdid": "int - ID для пагинации",
                "limit": "int - лимит записей (макс 100000)"
            },
            "response": {
                "data": "array - продажи с детализацией"
            },
            "use_cases": [
                "Анализ продаж за период",
                "Расчет прибыли",
                "Топ продаваемых товаров"
            ]
        },
        {
            "name": "get_orders_report",
            "description": "Получение отчета о заказах",
            "endpoint": "/api/v1/supplier/orders",
            "method": "GET",
            "category": "statistics",
            "params": {
                "dateFrom": "string - дата начала",
                "dateTo": "string - дата окончания",
                "limit": "int - лимит"
            },
            "response": {
                "data": "array - заказы с детализацией"
            },
            "use_cases": [
                "Анализ заказов",
                "Конверсия в продажи",
                "Средний чек"
            ]
        },
        {
            "name": "get_report_detail_by_period",
            "description": "Детальный отчет по реализации с финансовыми показателями",
            "endpoint": "/api/v5/supplier/reportDetailByPeriod",
            "method": "GET",
            "category": "statistics",
            "params": {
                "dateFrom": "string - дата начала",
                "dateTo": "string - дата окончания",
                "limit": "int - лимит"
            },
            "response": {
                "data": "array - детальная реализация с себестоимостью"
            },
            "use_cases": [
                "Расчет чистой прибыли",
                "Анализ комиссий",
                "Финансовый учет"
            ]
        },
        {
            "name": "get_incomes",
            "description": "Получение поставок на склады WB",
            "endpoint": "/api/v1/supplier/incomes",
            "method": "GET",
            "category": "statistics",
            "params": {
                "dateFrom": "string - дата начала",
                "limit": "int - лимит"
            },
            "response": {
                "data": "array - поставки с датами и статусами"
            },
            "use_cases": [
                "Отслеживание поставок",
                "История приемки"
            ]
        },
        {
            "name": "get_stocks_report",
            "description": "Отчет по остаткам на складах WB",
            "endpoint": "/api/v1/supplier/stocks",
            "method": "GET",
            "category": "statistics",
            "params": {
                "dateFrom": "string - дата"
            },
            "response": {
                "data": "array - остатки по складам"
            },
            "use_cases": [
                "Анализ запасов",
                "Товары с низкими остатками"
            ]
        },
        
        # ==========================================
        # ЗАКАЗЫ (Orders)
        # ==========================================
        {
            "name": "get_fbs_orders",
            "description": "Получение заказов FBS (отгрузка с моего склада)",
            "endpoint": "/api/v3/orders",
            "method": "GET",
            "category": "marketplace",
            "params": {
                "limit": "int - лимит (макс 1000)",
                "next": "int - ID для пагинации",
                "dateFrom": "string - дата с которой получать заказы"
            },
            "response": {
                "orders": "array - заказы FBS",
                "next": "int - ID для следующей страницы"
            },
            "use_cases": [
                "Получение новых заказов",
                "Обработка сборки",
                "Архив заказов"
            ]
        },
        {
            "name": "get_order_details",
            "description": "Получение деталей конкретного заказа",
            "endpoint": "/api/v3/orders/{orderId}",
            "method": "GET",
            "category": "marketplace",
            "params": {
                "orderId": "int - ID заказа (в URL)"
            },
            "response": {
                "order": "object - детали заказа"
            },
            "use_cases": [
                "Проверка состава заказа",
                "Информация для упаковки"
            ]
        },
        {
            "name": "confirm_order_assembly",
            "description": "Подтверждение сборки заказа FBS",
            "endpoint": "/api/v3/orders/{orderId}/confirm",
            "method": "PATCH",
            "category": "marketplace",
            "params": {
                "orderId": "int - ID заказа (в URL)",
                "sticker": "object - данные стикера"
            },
            "response": {},
            "use_cases": [
                "Подтверждение готовности к отгрузке",
                "Сборка заказа"
            ]
        },
        {
            "name": "cancel_order",
            "description": "Отмена заказа",
            "endpoint": "/api/v3/orders/{orderId}/cancel",
            "method": "PATCH",
            "category": "marketplace",
            "params": {
                "orderId": "int - ID заказа (в URL)",
                "reason": "string - причина отмены"
            },
            "response": {},
            "use_cases": [
                "Отмена невыполнимого заказа",
                "Нет в наличии"
            ]
        },
        
        # ==========================================
        # РЕКЛАМА И ПРОДВИЖЕНИЕ (Promotion)
        # ==========================================
        {
            "name": "get_advert_campaigns",
            "description": "Получение списка рекламных кампаний",
            "endpoint": "/adv/v1/promotion/adverts",
            "method": "GET",
            "category": "advert",
            "params": {
                "status": "int - статус кампании",
                "type": "int - тип кампании (4-каталог, 5-карточка, 6-поиск, 7-рекомендации)",
                "limit": "int - лимит",
                "offset": "int - смещение"
            },
            "response": {
                "adverts": "array - список кампаний"
            },
            "use_cases": [
                "Просмотр активных кампаний",
                "Управление рекламой"
            ]
        },
        {
            "name": "get_campaign_stats",
            "description": "Статистика рекламных кампаний",
            "endpoint": "/adv/v3/fullstats",
            "method": "GET",
            "category": "advert",
            "params": {
                "id": "array - ID кампаний"
            },
            "response": {
                "stats": "array - статистика по кампаниям"
            },
            "use_cases": [
                "ROI рекламы",
                "Эффективность кампаний",
                "Оптимизация бюджета"
            ]
        },
        {
            "name": "create_campaign",
            "description": "Создание рекламной кампании",
            "endpoint": "/adv/v2/seacat/save-ad",
            "method": "POST",
            "category": "advert",
            "params": {
                "name": "string - название кампании",
                "nms": "array - артикулы товаров",
                "bid": "int - ставка",
                "type": "int - тип кампании"
            },
            "response": {
                "advertId": "int - ID созданной кампании"
            },
            "use_cases": [
                "Запуск рекламы на новые товары",
                "Продвижение в поиске"
            ]
        },
        {
            "name": "update_campaign_bid",
            "description": "Изменение ставки рекламной кампании",
            "endpoint": "/api/advert/v1/bids",
            "method": "PATCH",
            "category": "advert",
            "params": {
                "advertIds": "array - ID кампаний",
                "bid": "int - новая ставка"
            },
            "response": {},
            "use_cases": [
                "Автоматическая корректировка ставок",
                "Управление CPC"
            ]
        },
        {
            "name": "pause_campaign",
            "description": "Приостановка рекламной кампании",
            "endpoint": "/adv/v0/pause",
            "method": "GET",
            "category": "advert",
            "params": {
                "id": "int - ID кампании (query param)"
            },
            "response": {},
            "use_cases": [
                "Пауза неэффективной кампании",
                "Управление бюджетом"
            ]
        },
        {
            "name": "start_campaign",
            "description": "Запуск рекламной кампании",
            "endpoint": "/adv/v0/start",
            "method": "GET",
            "category": "advert",
            "params": {
                "id": "int - ID кампании (query param)"
            },
            "response": {},
            "use_cases": [
                "Запуск кампании",
                "Возобновление после паузы"
            ]
        },
        {
            "name": "delete_campaign",
            "description": "Удаление рекламной кампании",
            "endpoint": "/adv/v0/delete",
            "method": "GET",
            "category": "advert",
            "params": {
                "id": "int - ID кампании (query param)"
            },
            "response": {},
            "use_cases": [
                "Удаление завершенных кампаний",
                "Очистка архива"
            ]
        },
        {
            "name": "get_campaign_budget",
            "description": "Получение бюджета кампании",
            "endpoint": "/adv/v1/budget",
            "method": "GET",
            "category": "advert",
            "params": {
                "id": "int - ID кампании (query param)"
            },
            "response": {
                "budget": "float - текущий бюджет",
                "total": "float - всего потрачено"
            },
            "use_cases": [
                "Проверка остатка бюджета",
                "Пополнение при необходимости"
            ]
        },
        
        # ==========================================
        # ПРЕДМЕТЫ И ХАРАКТЕРИСТИКИ (Subjects & Characteristics)
        # ==========================================
        {
            "name": "get_subject_characteristics",
            "description": "Получение характеристик предмета для создания карточки",
            "endpoint": "/content/v2/object/charcs/{subjectId}",
            "method": "GET",
            "category": "content",
            "params": {
                "subjectId": "int - ID предмета (в URL)"
            },
            "response": {
                "data": "array - обязательные и опциональные характеристики"
            },
            "use_cases": [
                "Подготовка карточки товара",
                "Проверка обязательных полей"
            ]
        },
        
        # ==========================================
        # ОТЗЫВЫ И ВОПРОСЫ (Feedbacks & Questions)
        # ==========================================
        {
            "name": "get_feedbacks",
            "description": "Получение отзывов покупателей",
            "endpoint": "/api/v1/feedbacks",
            "method": "GET",
            "category": "statistics",
            "params": {
                "isAnswered": "bool - только с ответом/без",
                "take": "int - количество",
                "skip": "int - пропустить"
            },
            "response": {
                "data": "array - отзывы с оценками"
            },
            "use_cases": [
                "Мониторинг репутации",
                "Анализ жалоб",
                "Ответы на отзывы"
            ]
        },
        {
            "name": "reply_to_feedback",
            "description": "Ответ на отзыв покупателя",
            "endpoint": "/api/v1/feedbacks/answer",
            "method": "POST",
            "category": "statistics",
            "params": {
                "id": "string - ID отзыва",
                "text": "string - текст ответа"
            },
            "response": {},
            "use_cases": [
                "Работа с негативом",
                "Благодарность за положительный отзыв"
            ]
        },
        {
            "name": "get_questions",
            "description": "Получение вопросов покупателей",
            "endpoint": "/api/v1/questions",
            "method": "GET",
            "category": "statistics",
            "params": {
                "isAnswered": "bool - статус ответа",
                "take": "int - количество"
            },
            "response": {
                "data": "array - вопросы"
            },
            "use_cases": [
                "Обработка вопросов",
                "Улучшение описаний"
            ]
        },
        
        # ==========================================
        # АНАЛИТИКА И ПОИСК (Analytics)
        # ==========================================
        {
            "name": "get_search_queries",
            "description": "Получение поисковых запросов, по которым находят товары",
            "endpoint": "/api/v1/search-queries",
            "method": "GET",
            "category": "analytics",
            "params": {
                "dateFrom": "string - дата начала",
                "dateTo": "string - дата окончания"
            },
            "response": {
                "data": "array - поисковые фразы и частота"
            },
            "use_cases": [
                "SEO оптимизация",
                "Подбор ключевых слов",
                "Анализ спроса"
            ]
        },
        
        # ==========================================
        # ТАРИФЫ И ФИНАНСЫ (Tariffs)
        # ==========================================
        {
            "name": "get_tariffs",
            "description": "Получение текущих тарифов на хранение и доставку",
            "endpoint": "/api/v1/tariffs",
            "method": "GET",
            "category": "tariffs",
            "params": {},
            "response": {
                "data": "array - тарифы по складам"
            },
            "use_cases": [
                "Расчет себестоимости",
                "Выбор склада",
                "Планирование бюджета"
            ]
        },
    ]
    
    @classmethod
    def find_method(cls, query: str) -> List[Dict[str, Any]]:
        """
        Находит подходящие методы API по описанию.
        
        Args:
            query: Описание задачи на естественном языке
            
        Returns:
            Список подходящих методов, отсортированных по релевантности
        """
        query_lower = query.lower()
        matching_methods = []
        
        for method in cls.METHODS:
            score = 0
            
            # Проверяем описание метода
            if any(word in method["description"].lower() for word in query_lower.split()):
                score += 2
            
            # Проверяем название метода
            if any(word in method["name"].lower() for word in query_lower.split()):
                score += 1
            
            # Проверяем use cases
            for use_case in method.get("use_cases", []):
                if any(word in use_case.lower() for word in query_lower.split()):
                    score += 1
                    break
            
            if score > 0:
                matching_methods.append((score, method))
        
        # Сортируем по релевантности
        matching_methods.sort(key=lambda x: x[0], reverse=True)
        
        return [method for score, method in matching_methods[:5]]
    
    @classmethod
    def get_method_by_name(cls, name: str) -> Dict[str, Any]:
        """Получить метод по его названию"""
        for method in cls.METHODS:
            if method["name"] == name:
                return method
        return None
    
    @classmethod
    def list_all_methods(cls) -> List[str]:
        """Возвращает список всех доступных методов"""
        return [method["name"] for method in cls.METHODS]
    
    @classmethod
    def get_methods_by_category(cls, category: str) -> List[Dict[str, Any]]:
        """Получить все методы определенной категории"""
        return [method for method in cls.METHODS if method["category"] == category]


# Удобные алиасы для быстрого доступа
CONTENT_METHODS = WBMethodRegistry.get_methods_by_category("content")
STATISTICS_METHODS = WBMethodRegistry.get_methods_by_category("statistics")
MARKETPLACE_METHODS = WBMethodRegistry.get_methods_by_category("marketplace")
ADVERT_METHODS = WBMethodRegistry.get_methods_by_category("advert")
ANALYTICS_METHODS = WBMethodRegistry.get_methods_by_category("analytics")
