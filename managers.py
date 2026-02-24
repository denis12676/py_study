"""
Модули для работы с конкретными функциями Wildberries

Каждый класс отвечает за свою область:
- ProductsManager - управление товарами и ценами
- AnalyticsManager - аналитика и отчеты
- OrdersManager - заказы и отгрузки
- AdvertisingManager - реклама и продвижение
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import time
import json
from wb_client import WildberriesAPI, WBConfig, API_ENDPOINTS


class ProductsManager:
    """Управление товарами, ценами и остатками"""
    
    def __init__(self, api: WildberriesAPI):
        self.api = api
    
    def get_all_products(self, limit: int = 100) -> List[Dict]:
        """
        Получить все товары продавца с ценами
        Использует актуальный метод POST /content/v2/get/cards/list
        
        Args:
            limit: Количество товаров за запрос (макс 100)
            
        Returns:
            Список товаров с информацией о ценах и остатках
        """
        response = self.api.post(
            "/content/v2/get/cards/list",
            data={
                "settings": {
                    "cursor": {
                        "limit": limit
                    },
                    "filter": {
                        "withPhoto": -1
                    }
                }
            },
            base_url=self.api.config.content_url
        )
        return response.get("cards", [])
    
    def search_products(self, query: str, limit: int = 100) -> List[Dict]:
        """
        Поиск товаров по артикулу или названию
        Использует метод POST /content/v2/get/cards/list с фильтром textSearch
        
        Args:
            query: Поисковый запрос
            limit: Лимит результатов
            
        Returns:
            Найденные товары
        """
        response = self.api.post(
            "/content/v2/get/cards/list",
            data={
                "settings": {
                    "cursor": {
                        "limit": limit
                    },
                    "filter": {
                        "textSearch": query,
                        "withPhoto": -1
                    }
                }
            },
            base_url=self.api.config.content_url
        )
        return response.get("cards", [])
    
    def get_products_with_prices(self, limit: int = 1000, offset: int = 0, search: str = None) -> List[Dict]:
        """
        Получение товаров с ценами и скидками через Prices API
        Использует метод GET /api/v2/list/goods/filter
        
        Args:
            limit: Лимит записей (макс 1000)
            offset: Смещение для пагинации
            search: Поисковый запрос (опционально)
            
        Returns:
            Список товаров с ценами и скидками
        """
        params = {"limit": limit, "offset": offset}
        if search:
            params["search"] = search
            
        response = self.api.get(
            "/api/v2/list/goods/filter",
            params=params,
            base_url=API_ENDPOINTS["prices"]
        )
        return response.get("data", {}).get("listGoods", [])
    
    def get_product_sizes_with_prices(self, nm_id: int) -> List[Dict]:
        """
        Получение размеров товара с ценами
        Использует метод GET /api/v2/list/goods/size/nm
        
        Args:
            nm_id: Артикул товара (nmID)
            
        Returns:
            Список размеров с ценами
        """
        response = self.api.get(
            f"/api/v2/list/goods/size/nm",
            params={"nmId": nm_id},
            base_url=API_ENDPOINTS["prices"]
        )
        return response.get("data", {}).get("listGoods", [])
    
    def update_price(self, nm_id: int, price: float, discount: Optional[int] = None) -> Dict:
        """
        Обновить цену товара
        
        Args:
            nm_id: Артикул WB (nmID)
            price: Новая цена
            discount: Скидка в процентах (опционально)
            
        Returns:
            Информация о задаче обновления
        """
        data = {
            "data": [{
                "nmID": nm_id,
                "price": price
            }]
        }
        
        if discount is not None:
            data["data"][0]["discount"] = discount
        
        return self.api.post(
            "/api/v2/upload/task",
            data=data,
            base_url=self.api.config.content_url
        )
    
    def update_multiple_prices(self, price_data: List[Dict]) -> Dict:
        """
        Массовое обновление цен
        
        Args:
            price_data: Список словарей с nmID, price и discount
            Пример: [{"nmID": 123, "price": 1000, "discount": 10}, ...]
            
        Returns:
            Информация о задаче обновления
        """
        return self.api.post(
            "/api/v2/upload/task",
            data={"data": price_data},
            base_url=self.api.config.content_url
        )
    
    def get_quarantine_products(self) -> List[Dict]:
        """
        Получить товары в карантине (не обновлялись более 30 дней)
        
        Returns:
            Список товаров в карантине
        """
        response = self.api.get(
            "/api/v2/quarantine/goods",
            base_url=self.api.config.content_url
        )
        return response.get("data", [])
    
    def get_product_categories(self) -> List[Dict]:
        """
        Получить список категорий товаров
        
        Returns:
            Список категорий
        """
        response = self.api.get(
            "/content/v2/object/parent/all",
            base_url=self.api.config.content_url
        )
        return response.get("data", [])
    
    def get_warehouses(self) -> List[Dict]:
        """
        Получить список складов продавца
        
        Returns:
            Список складов
        """
        response = self.api.get(
            "/api/v3/warehouses",
            base_url=API_ENDPOINTS["marketplace"]
        )
        return response if isinstance(response, list) else response.get("data", [])
    
    def get_all_chrt_ids(self) -> List[int]:
        """
        Получить все chrtIds (ID размеров) товаров продавца
        
        Returns:
            Список chrtIds для всех товаров
        """
        chrt_ids = []
        try:
            # Content API имеет лимит 100 товаров за запрос, используем пагинацию
            cursor = {"limit": 100}
            total_cards = 0
            
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
                    print(f"WARNING: Неожиданный ответ от Content API: {type(response)}")
                    break
                
                if 'error' in response and response.get('error'):
                    error_text = response.get('errorText', 'Unknown error')
                    print(f"ERROR: Content API error: {error_text}")
                    break
                
                cards = response.get('cards', [])
                if not cards:
                    break
                
                total_cards += len(cards)
                
                for card in cards:
                    sizes = card.get('sizes', [])
                    for size in sizes:
                        chrt_id = size.get('chrtID')
                        if chrt_id:
                            chrt_ids.append(chrt_id)
                
                # Проверяем есть ли еще товары
                response_cursor = response.get('cursor', {})
                total = response_cursor.get('total', 0)
                
                if len(cards) < 100 or total_cards >= total:
                    break
                
                # Обновляем cursor для следующей страницы
                last_card = cards[-1]
                cursor = {
                    "limit": 100,
                    "updatedAt": last_card.get('updatedAt'),
                    "nmID": last_card.get('nmID')
                }
            
            print(f"INFO: Получено {total_cards} карточек, {len(chrt_ids)} chrtIds")
            return chrt_ids
            
        except Exception as e:
            print(f"ERROR: Ошибка получения chrtIds: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def get_chrt_id_mapping(self) -> Dict[int, Dict]:
        """
        Получить соответствие chrtId → информация о товаре
        
        Returns:
            Словарь {chrtId: {'nmId': ..., 'vendorCode': ..., 'title': ..., 'brand': ...}}
        """
        mapping = {}
        try:
            cursor = {"limit": 100}
            total_cards = 0
            
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
                
                if 'error' in response and response.get('error'):
                    break
                
                cards = response.get('cards', [])
                if not cards:
                    break
                
                total_cards += len(cards)
                
                for card in cards:
                    nm_id = card.get('nmID')
                    vendor_code = card.get('vendorCode', '')
                    title = card.get('title', '')
                    brand = card.get('brand', '')
                    sizes = card.get('sizes', [])
                    
                    for size in sizes:
                        chrt_id = size.get('chrtID')
                        if chrt_id:
                            mapping[chrt_id] = {
                                'nmId': nm_id,
                                'vendorCode': vendor_code,
                                'title': title,
                                'brand': brand,
                                'techSize': size.get('techSize', ''),
                                'wbSize': size.get('wbSize', '')
                            }
                
                response_cursor = response.get('cursor', {})
                total = response_cursor.get('total', 0)
                
                if len(cards) < 100 or total_cards >= total:
                    break
                
                last_card = cards[-1]
                cursor = {
                    "limit": 100,
                    "updatedAt": last_card.get('updatedAt'),
                    "nmID": last_card.get('nmID')
                }
            
            return mapping
            
        except Exception as e:
            print(f"ERROR: Ошибка получения chrtId mapping: {e}")
            return {}
    
    def get_stocks(self, warehouse_id: int, chrt_ids: List[int] = None) -> List[Dict]:
        """
        Получить остатки на конкретном складе продавца (FBS)
        
        Args:
            warehouse_id: ID склада продавца
            chrt_ids: Список ID размеров товаров. Если None - получает автоматически.
            
        Returns:
            Остатки товаров с информацией о товаре (vendorCode, nmId, название)
        """
        try:
            # Получаем маппинг chrtId → информация о товаре
            chrt_mapping = self.get_chrt_id_mapping()
            
            # Если chrtIds не переданы - получаем все из маппинга
            if chrt_ids is None:
                chrt_ids = list(chrt_mapping.keys())
            
            if not chrt_ids:
                print("WARNING: Нет chrtIds для запроса остатков")
                return []
            
            # API принимает максимум 1000 chrtIds за раз
            all_stocks = []
            batch_size = 1000
            
            for i in range(0, len(chrt_ids), batch_size):
                batch = chrt_ids[i:i + batch_size]
                
                payload = {
                    "chrtIds": batch,
                    "skus": []  # Deprecated
                }
                
                response = self.api.post(
                    f"/api/v3/stocks/{warehouse_id}",
                    data=payload,
                    base_url=API_ENDPOINTS["marketplace"]
                )
                
                if isinstance(response, dict):
                    stocks = response.get('stocks', [])
                    # Добавляем информацию о товаре к каждому остатку
                    for stock in stocks:
                        chrt_id = stock.get('chrtId')
                        if chrt_id and chrt_id in chrt_mapping:
                            stock.update(chrt_mapping[chrt_id])
                        else:
                            # Если нет в маппинге, добавляем минимальную информацию
                            stock['nmId'] = None
                            stock['vendorCode'] = ''
                            stock['title'] = ''
                            stock['brand'] = ''
                    all_stocks.extend(stocks)
                elif isinstance(response, list):
                    all_stocks.extend(response)
            
            return all_stocks
            
        except Exception as e:
            print(f"ERROR: Ошибка получения остатков: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def get_all_fbs_stocks(self) -> Dict[int, List[Dict]]:
        """
        Получить остатки со всех складов продавца (FBS)
        
        Returns:
            Словарь {warehouse_id: [остатки]}
        """
        try:
            # Получаем список всех складов
            warehouses = self.get_warehouses()
            if not warehouses:
                print("WARNING: Нет складов FBS")
                return {}
            
            # Получаем все chrtIds один раз
            chrt_ids = self.get_all_chrt_ids()
            if not chrt_ids:
                print("WARNING: Нет chrtIds")
                return {}
            
            print(f"INFO: Получено {len(chrt_ids)} chrtIds для {len(warehouses)} складов")
            
            all_stocks = {}
            for warehouse in warehouses:
                wh_id = warehouse.get('id')
                wh_name = warehouse.get('name', 'Unknown')
                if wh_id:
                    stocks = self.get_stocks(wh_id, chrt_ids)
                    if stocks:
                        all_stocks[wh_id] = stocks
                        print(f"INFO: Склад {wh_name}: {len(stocks)} товаров")
            
            return all_stocks
            
        except Exception as e:
            print(f"ERROR: Ошибка получения всех остатков FBS: {e}")
            import traceback
            traceback.print_exc()
            return {}
    
    def get_total_stocks_by_product(self) -> Dict[int, Dict]:
        """
        Получить суммарные остатки FBS + FBO для каждого товара
        
        Returns:
            Словарь {nmId: {'fbs': сумма, 'fbo': сумма, 'total': сумма, 'details': {...}}}
        """
        result = {}
        
        try:
            # 1. Получаем остатки FBS со всех складов
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
            
            # 2. Получаем остатки FBO
            fbo_data = self.get_fbo_stocks()
            fbo_regions = fbo_data.get('regions', [])
            
            for region in fbo_regions:
                for office in region.get('offices', []):
                    # FBO API возвращает агрегированные данные по офисам,
                    # но без разбивки по товарам. Для детальной информации 
                    # нужно использовать другие методы.
                    pass
            
            # 3. Считаем total
            for nm_id in result:
                result[nm_id]['total'] = result[nm_id]['fbs'] + result[nm_id]['fbo']
            
            return result
            
        except Exception as e:
            print(f"ERROR: Ошибка получения суммарных остатков: {e}")
            import traceback
            traceback.print_exc()
            return {}
    
    def get_fbo_stocks(self) -> Dict:
        """
        Получить остатки на складах WB (FBO)
        
        Использует метод POST /api/v2/stocks-report/offices из Analytics API
        с stockType="wb" для получения остатков на складах Wildberries
        
        Returns:
            Словарь с данными по регионам и офисам (складам)
        """
        try:
            today = datetime.now().strftime("%Y-%m-%d")
            
            response = self.api.post(
                "/api/v2/stocks-report/offices",
                data={
                    "nmIDs": [],
                    "subjectIDs": [],
                    "brandNames": [],
                    "tagIDs": [],
                    "currentPeriod": {
                        "start": today,
                        "end": today
                    },
                    "stockType": "wb",  # склады WB (FBO)
                    "skipDeletedNm": True
                },
                base_url=API_ENDPOINTS["analytics"]
            )
            
            if isinstance(response, dict) and 'data' in response:
                return response['data']
            else:
                return {"regions": []}
                
        except Exception as e:
            print(f"ERROR: Ошибка получения остатков FBO: {e}")
            return {"regions": []}
    
    def get_fbo_stocks_detailed(self) -> List[Dict]:
        """
        Получить детальные остатки FBO с информацией по товарам (включая vendorCode)
        
        Использует метод POST /api/v2/stocks-report/products/groups из Analytics API
        с stockType="wb" для получения остатков по каждому товару
        
        Returns:
            Список товаров с остатками на FBO складах
        """
        try:
            # Сначала получаем маппинг nmId -> vendorCode, title, brand
            product_mapping = {}
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
                        product_mapping[nm_id] = {
                            'vendorCode': card.get('vendorCode', ''),
                            'title': card.get('title', ''),
                            'brand': card.get('brand', ''),
                            'subjectName': card.get('subjectName', ''),
                            'nmId': nm_id
                        }
                
                # Проверяем есть ли еще товары
                response_cursor = response.get('cursor', {})
                total = response_cursor.get('total', 0)
                
                if len(cards) < 100 or len(product_mapping) >= total:
                    break
                
                # Обновляем cursor для следующей страницы
                last_card = cards[-1]
                cursor = {
                    "limit": 100,
                    "updatedAt": last_card.get('updatedAt'),
                    "nmID": last_card.get('nmID')
                }
            
            print(f"INFO: Получено {len(product_mapping)} товаров для FBO")
            print(f"DEBUG: Первые 3 товара из mapping: {list(product_mapping.items())[:3]}")
            
            # Теперь получаем остатки FBO с детализацией
            today = datetime.now().strftime("%Y-%m-%d")
            
            # Запрашиваем остатки без фильтрации по nmIds (получаем все)
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
                    "availabilityFilters": [],  # Обязательный параметр
                    "orderBy": {
                        "field": "avgOrders",  # Пробуем поле из примера документации
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
                print(f"DEBUG: API вернул {len(groups)} групп товаров")
                
                for group in groups[:3]:  # Первые 3 для отладки
                    nm_id = group.get('nmID')
                    print(f"DEBUG: Обрабатываем nmID={nm_id}, есть в mapping: {nm_id in product_mapping}")
                
                for group in groups:
                    nm_id = group.get('nmID')
                    if nm_id and nm_id in product_mapping:
                        # Добавляем информацию о товаре
                        product_info = product_mapping[nm_id]
                        
                        # Получаем метрики остатков
                        stocks = group.get('stocks', [])
                        total_stock = sum(s.get('stock', 0) for s in stocks)
                        
                        result.append({
                            'nmId': nm_id,
                            'vendorCode': product_info['vendorCode'],
                            'title': product_info['title'],
                            'brand': product_info['brand'],
                            'subject': product_info['subjectName'],
                            'stockCount': total_stock,
                            'stocks': stocks
                        })
                    elif nm_id:
                        # nmID есть в API ответе, но нет в mapping
                        print(f"DEBUG: nmID {nm_id} не найден в product_mapping")
                        result.append({
                            'nmId': nm_id,
                            'vendorCode': '',
                            'title': '',
                            'brand': '',
                            'subject': '',
                            'stockCount': sum(s.get('stock', 0) for s in group.get('stocks', [])),
                            'stocks': group.get('stocks', [])
                        })
            
            print(f"INFO: Сформировано {len(result)} записей с товарами")
            return result
            
        except Exception as e:
            print(f"ERROR: Ошибка получения детальных остатков FBO: {e}")
            import traceback
            traceback.print_exc()
            return []


class AnalyticsManager:
    """Аналитика продаж и отчеты"""
    
    def __init__(self, api: WildberriesAPI):
        self.api = api
        # Кэш для данных
        self._cache = {}
        self._cache_ttl = 600  # 10 минут (увеличено с 5)
        self._last_api_call = 0  # Время последнего API вызова
    
    def _get_cache_key(self, method: str, **kwargs) -> str:
        """Создает ключ кэша на основе метода и параметров"""
        import hashlib
        params_str = json.dumps(kwargs, sort_keys=True, default=str)
        return f"{method}:{hashlib.md5(params_str.encode()).hexdigest()}"
    
    def _get_cached(self, cache_key: str) -> Optional[Any]:
        """Получает данные из кэша если они еще актуальны"""
        if cache_key in self._cache:
            data, timestamp = self._cache[cache_key]
            if time.time() - timestamp < self._cache_ttl:
                return data
            else:
                del self._cache[cache_key]
        return None
    
    def _wait_between_calls(self, min_interval: float = 1.0):
        """Ожидание между API вызовами для предотвращения 429"""
        current_time = time.time()
        elapsed = current_time - self._last_api_call
        if elapsed < min_interval:
            time.sleep(min_interval - elapsed)
        self._last_api_call = time.time()
    
    def _set_cached(self, cache_key: str, data: Any):
        """Сохраняет данные в кэш"""
        self._cache[cache_key] = (data, time.time())
    
    def clear_cache(self):
        """Очистить кэш"""
        self._cache.clear()
    
    def get_sales(
        self, 
        date_from: Optional[str] = None, 
        date_to: Optional[str] = None,
        limit: int = 1000
    ) -> List[Dict]:
        """
        Получить отчет о продажах
        
        Args:
            date_from: Дата начала (YYYY-MM-DD), по умолчанию сегодня - 30 дней
            date_to: Дата окончания (YYYY-MM-DD), по умолчанию сегодня
            limit: Лимит записей
            
        Returns:
            Список продаж с детализацией
        """
        if not date_from:
            date_from = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        if not date_to:
            date_to = datetime.now().strftime("%Y-%m-%d")
        
        # Проверяем кэш
        cache_key = self._get_cache_key("get_sales", date_from=date_from, date_to=date_to, limit=limit)
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached
        
        # Ждем между вызовами API
        self._wait_between_calls(2.0)  # Минимум 2 секунды между запросами
        
        response = self.api.get(
            "/api/v1/supplier/sales",
            params={
                "dateFrom": date_from,
                "dateTo": date_to,
                "limit": limit
            },
            base_url=API_ENDPOINTS["statistics"]
        )
        result = response if isinstance(response, list) else []
        
        # Сохраняем в кэш
        self._set_cached(cache_key, result)
        
        return result
    
    def get_orders(
        self, 
        date_from: Optional[str] = None, 
        date_to: Optional[str] = None,
        limit: int = 1000
    ) -> List[Dict]:
        """
        Получить отчет о заказах
        
        Args:
            date_from: Дата начала (YYYY-MM-DD)
            date_to: Дата окончания (YYYY-MM-DD)
            limit: Лимит записей
            
        Returns:
            Список заказов
        """
        if not date_from:
            date_from = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        if not date_to:
            date_to = datetime.now().strftime("%Y-%m-%d")
        
        response = self.api.get(
            "/api/v1/supplier/orders",
            params={
                "dateFrom": date_from,
                "dateTo": date_to,
                "limit": limit
            },
            base_url=API_ENDPOINTS["statistics"]
        )
        return response if isinstance(response, list) else []
    
    def get_detailed_report(
        self, 
        date_from: Optional[str] = None, 
        date_to: Optional[str] = None,
        limit: int = 1000
    ) -> List[Dict]:
        """
        Получить детальный отчет по реализации с финансовыми показателями
        
        Args:
            date_from: Дата начала (YYYY-MM-DD)
            date_to: Дата окончания (YYYY-MM-DD)
            limit: Лимит записей
            
        Returns:
            Детальный отчет с себестоимостью и комиссиями
        """
        if not date_from:
            date_from = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        if not date_to:
            date_to = datetime.now().strftime("%Y-%m-%d")
        
        # Проверяем кэш
        cache_key = self._get_cache_key("get_detailed_report", date_from=date_from, date_to=date_to, limit=limit)
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached
        
        response = self.api.get(
            "/api/v5/supplier/reportDetailByPeriod",
            params={
                "dateFrom": date_from,
                "dateTo": date_to,
                "limit": limit
            },
            base_url=API_ENDPOINTS["statistics"]
        )
        result = response if isinstance(response, list) else []
        
        # Сохраняем в кэш
        self._set_cached(cache_key, result)
        
        return result
    
    def calculate_revenue(self, days: int = 30) -> Dict[str, Any]:
        """
        Рассчитать выручку за период
        
        Использует поле forPay из отчета sales - это сумма к выплате 
        с учетом всех скидок и комиссии WB
        
        Args:
            days: Количество дней для анализа
            
        Returns:
            Словарь с выручкой, количеством продаж и средним чеком
        """
        date_from = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        sales = self.get_sales(date_from=date_from)
        
        # Используем forPay - это сумма к выплате (с учетом всех вычетов)
        # totalPrice - это цена без скидок (завышенная)
        # Фильтруем возвраты из суммы выручки
        total_revenue = sum(
            float(sale.get("forPay", 0) or 0) 
            for sale in sales 
            if not sale.get("isCancel", False) and not sale.get("isReturn", False)
        )
        total_sales = len(sales)  # Все записи (включая возвраты)
        avg_check = total_revenue / total_sales if total_sales > 0 else 0
        
        return {
            "period_days": days,
            "total_revenue": round(total_revenue, 2),
            "total_sales": total_sales,
            "average_check": round(avg_check, 2)
        }
    
    def calculate_revenue_detailed(self, days: int = 30) -> Dict[str, Any]:
        """
        Рассчитать детальную выручку с учетом возвратов, комиссий и штрафов
        
        Args:
            days: Количество дней для анализа
            
        Returns:
            Словарь с полной финансовой информацией:
            - total_revenue: Валовая выручка (без вычетов)
            - net_revenue: Чистая к выплате (с учетом всех вычетов)
            - total_commission: Комиссия WB
            - total_returns: Сумма возвратов
            - total_logistics: Логистика
            - total_storage: Хранение
            - penalty: Штрафы
            - total_sales: Количество операций
            - average_check: Средний чек
            - return_rate: Процент возвратов
        """
        date_from = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        
        # Используем детальный отчет (там есть forPay - сумма к выплате)
        report = self.get_detailed_report(date_from=date_from)
        
        if not report:
            return {
                "period_days": days,
                "total_revenue": 0,
                "net_revenue": 0,
                "total_commission": 0,
                "total_returns": 0,
                "total_logistics": 0,
                "total_storage": 0,
                "penalty": 0,
                "total_sales": 0,
                "average_check": 0,
                "return_rate": 0
            }
        
        total_revenue = 0      # Валовая выручка
        net_revenue = 0        # Чистая к выплате
        total_commission = 0   # Комиссия WB
        total_returns = 0      # Возвраты
        total_logistics = 0    # Логистика
        total_storage = 0      # Хранение
        penalty = 0            # Штрафы
        sales_count = 0        # Продажи
        returns_count = 0      # Количество возвратов
        
        for item in report:
            # Сумма к выплате (учитывает все вычеты)
            net_revenue += float(item.get("forPay", 0) or 0)
            
            # Проверяем тип операции
            is_return = item.get("isReturn", False)
            is_cancel = item.get("isCancel", False)
            
            if is_return or is_cancel:
                # Это возврат или отмена
                total_returns += float(item.get("retailAmount", 0) or 0)
                returns_count += 1
            else:
                # Это продажа
                total_revenue += float(item.get("retailAmount", 0) or 0)
                sales_count += 1
            
            # Комиссия WB
            total_commission += float(item.get("commissionAmount", 0) or 0)
            
            # Логистика
            total_logistics += float(item.get("deliveryAmount", 0) or 0)
            
            # Хранение
            total_storage += float(item.get("storageFee", 0) or 0)
            
            # Штрафы
            penalty += float(item.get("penalty", 0) or 0)
        
        total_operations = sales_count + returns_count
        
        return {
            "period_days": days,
            "total_revenue": round(total_revenue, 2),           # Валовая без возвратов
            "net_revenue": round(net_revenue, 2),              # Чистая к выплате
            "total_commission": round(total_commission, 2),    # Комиссия WB
            "total_returns": round(total_returns, 2),          # Сумма возвратов
            "total_logistics": round(total_logistics, 2),    # Логистика
            "total_storage": round(total_storage, 2),        # Хранение
            "penalty": round(penalty, 2),                      # Штрафы
            "total_sales": sales_count,                        # Количество продаж
            "total_returns_count": returns_count,              # Количество возвратов
            "total_operations": total_operations,            # Всего операций
            "average_check": round(total_revenue / sales_count, 2) if sales_count > 0 else 0,
            "average_net_check": round(net_revenue / sales_count, 2) if sales_count > 0 else 0,
            "return_rate": round((returns_count / total_operations * 100), 2) if total_operations > 0 else 0
        }
    
    def get_weekly_sales_report(self, week_start: Optional[str] = None) -> Dict[str, Any]:
        """
        Получить еженедельный отчет по продажам с детальной расшифровкой
        
        Этот метод собирает данные за неделю и группирует их:
        - По дням
        - По товарам (артикулам)
        - По брендам
        - По категориям
        
        Args:
            week_start: Дата начала недели (YYYY-MM-DD). Если None - берется прошлая неделя
            
        Returns:
            Детальный отчет с разбивкой по дням и товарам
        """
        import pandas as pd
        
        if not week_start:
            # Берем прошлую неделю (с понедельника)
            today = datetime.now()
            days_since_monday = today.weekday()
            last_monday = today - timedelta(days=days_since_monday + 7)
            week_start = last_monday.strftime("%Y-%m-%d")
        
        week_end_dt = datetime.strptime(week_start, "%Y-%m-%d") + timedelta(days=7)
        week_end = week_end_dt.strftime("%Y-%m-%d")
        
        print(f"Загрузка данных за неделю: {week_start} - {week_end}")
        
        # Получаем все продажи за неделю (с пагинацией если нужно)
        all_sales = []
        date_from = week_start
        
        while True:
            batch = self.get_sales(date_from=date_from, limit=1000)
            if not batch:
                break
                
            all_sales.extend(batch)
            
            # Проверяем не вышли ли за неделю
            if len(batch) < 1000:
                break
                
            # Берем дату последней записи для следующего запроса
            last_date = batch[-1].get('date', '')
            if not last_date or last_date[:10] > week_end:
                break
                
            date_from = last_date[:10] + 'T' + last_date[11:19]
        
        if not all_sales:
            return {
                "week_start": week_start,
                "week_end": week_end,
                "total_sales": 0,
                "total_revenue": 0,
                "error": "Нет данных за указанную неделю"
            }
        
        # Создаем DataFrame для анализа
        df = pd.DataFrame(all_sales)
        
        # Конвертируем даты
        df['date'] = pd.to_datetime(df['date'])
        df['day'] = df['date'].dt.strftime('%Y-%m-%d')
        df['day_name'] = df['date'].dt.strftime('%A')
        
        # Конвертируем числовые поля
        df['forPay'] = pd.to_numeric(df.get('forPay', 0), errors='coerce').fillna(0)
        df['totalPrice'] = pd.to_numeric(df.get('totalPrice', 0), errors='coerce').fillna(0)
        df['finishedPrice'] = pd.to_numeric(df.get('finishedPrice', 0), errors='coerce').fillna(0)
        
        # Определяем возвраты
        df['is_return'] = df.get('isCancel', False) | (df.get('saleID', '').str.contains('R', na=False))
        
        # Расчет метрик
        total_revenue = df['forPay'].sum()
        total_sales = len(df[~df['is_return']])
        total_returns = len(df[df['is_return']])
        
        # Группировка по дням
        daily_stats = df.groupby('day').agg({
            'forPay': 'sum',
            'nmId': 'count',
            'is_return': 'sum'
        }).reset_index()
        daily_stats.columns = ['date', 'revenue', 'sales_count', 'returns_count']
        
        # Группировка по товарам (топ 20)
        product_stats = df.groupby(['nmId', 'subject', 'brand'], as_index=False).agg({
            'forPay': 'sum',
            'date': 'count',  # Количество продаж (используем date как счетчик)
            'is_return': 'sum'
        })
        product_stats.columns = ['nmId', 'subject', 'brand', 'revenue', 'quantity', 'returns']
        product_stats = product_stats.sort_values('revenue', ascending=False).head(20)
        
        # Группировка по категориям
        category_stats = df.groupby('subject').agg({
            'forPay': 'sum',
            'nmId': 'count'
        }).reset_index()
        category_stats.columns = ['category', 'revenue', 'sales']
        category_stats = category_stats.sort_values('revenue', ascending=False).head(10)
        
        return {
            "week_start": week_start,
            "week_end": week_end,
            "total_revenue": round(total_revenue, 2),
            "total_sales": int(total_sales),
            "total_returns": int(total_returns),
            "return_rate": round((total_returns / (total_sales + total_returns) * 100), 2) if (total_sales + total_returns) > 0 else 0,
            "average_check": round(total_revenue / total_sales, 2) if total_sales > 0 else 0,
            "daily_breakdown": daily_stats.to_dict('records'),
            "top_products": product_stats.to_dict('records'),
            "category_breakdown": category_stats.to_dict('records'),
            "raw_data_count": len(df)
        }
    
    def export_weekly_report_csv(self, week_start: Optional[str] = None) -> str:
        """
        Экспортировать еженедельный отчет в CSV
        
        Args:
            week_start: Дата начала недели (YYYY-MM-DD)
            
        Returns:
            Путь к созданному CSV файлу
        """
        import pandas as pd
        
        report = self.get_weekly_sales_report(week_start)
        
        if report.get('error'):
            return None
        
        # Создаем DataFrame для дневной статистики
        daily_df = pd.DataFrame(report['daily_breakdown'])
        
        # Формируем имя файла
        filename = f"weekly_report_{report['week_start']}_to_{report['week_end']}.csv"
        
        # Добавляем сводку
        summary_data = {
            'Показатель': [
                'Период с',
                'Период по', 
                'Общая выручка',
                'Количество продаж',
                'Количество возвратов',
                'Процент возвратов',
                'Средний чек'
            ],
            'Значение': [
                report['week_start'],
                report['week_end'],
                f"{report['total_revenue']:.2f} ₽",
                report['total_sales'],
                report['total_returns'],
                f"{report['return_rate']:.2f}%",
                f"{report['average_check']:.2f} ₽"
            ]
        }
        summary_df = pd.DataFrame(summary_data)
        
        # Сохраняем
        with open(filename, 'w', encoding='utf-8-sig') as f:
            f.write("# СВОДКА\n")
            summary_df.to_csv(f, index=False)
            f.write("\n# ДНЕВНАЯ РАЗБИВКА\n")
            daily_df.to_csv(f, index=False)
        
        return filename
    
    def get_top_products(self, days: int = 30, limit: int = 10) -> List[Dict]:
        """
        Получить топ продаваемых товаров
        
        Args:
            days: Период анализа
            limit: Количество товаров
            
        Returns:
            Список топовых товаров
        """
        date_from = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        sales = self.get_sales(date_from=date_from)
        
        # Группируем по артикулу
        products = {}
        for sale in sales:
            nm_id = sale.get("nmId")
            if nm_id not in products:
                products[nm_id] = {
                    "nm_id": nm_id,
                    "name": sale.get("subject", "Unknown"),
                    "article": sale.get("supplierArticle", ""),
                    "quantity": 0,
                    "revenue": 0
                }
            # Count all sales including returns for quantity
            products[nm_id]["quantity"] += sale.get("quantity", 0) or 1  # Default to 1 if no quantity
            
            # Only add revenue for non-return/non-cancel sales
            is_return = sale.get("isCancel", False) or sale.get("isReturn", False)
            if not is_return:
                products[nm_id]["revenue"] += float(sale.get("forPay", 0) or 0)
        
        # Сортируем по выручке
        sorted_products = sorted(
            products.values(), 
            key=lambda x: x["revenue"], 
            reverse=True
        )
        
        return sorted_products[:limit]
    
    def get_stocks_report(self) -> List[Dict]:
        """
        Получить отчет по остаткам на складах WB
        
        Returns:
            Остатки по всем складам
        """
        date_from = datetime.now().strftime("%Y-%m-%d")
        response = self.api.get(
            "/api/v1/supplier/stocks",
            params={"dateFrom": date_from},
            base_url=API_ENDPOINTS["statistics"]
        )
        return response if isinstance(response, list) else []


class OrdersManager:
    """Управление заказами FBS, DBS"""
    
    def __init__(self, api: WildberriesAPI):
        self.api = api
    
    def get_new_orders(self, limit: int = 100) -> List[Dict]:
        """
        Получить новые заказы для сборки
        
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
        Подтвердить сборку заказа
        
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
        except:
            return False
    
    def cancel_order(self, order_id: int, reason: str = "Нет в наличии") -> bool:
        """
        Отменить заказ
        
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
        except:
            return False


class AdvertisingManager:
    """Управление рекламными кампаниями"""
    
    def __init__(self, api: WildberriesAPI):
        self.api = api
    
    def get_campaigns(self, status: Optional[int] = None) -> List[Dict]:
        """
        Получить список рекламных кампаний
        
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
        Получить статистику по кампаниям
        
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
        Создать рекламную кампанию
        
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
        Обновить ставку для кампаний
        
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
        except:
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
        except:
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
        except:
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
        except:
            return False
    
    def get_budget(self, campaign_id: int) -> Dict:
        """
        Получить бюджет кампании
        
        Returns:
            Информация о бюджете
        """
        return self.api.get(
            "/adv/v1/budget",
            params={"id": campaign_id},
            base_url=self.api.config.advert_url
        )
