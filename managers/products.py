"""
ProductsManager — управление товарами, ценами и категориями.
Каталог, поиск, обновление цен, chrtId маппинг.
"""

import logging
from typing import Dict, Any, List, Optional
from wb_client import WildberriesAPI, API_ENDPOINTS

logger = logging.getLogger(__name__)


class ProductsManager:
    """Управление товарами, ценами и категориями"""

    def __init__(self, api: WildberriesAPI):
        self.api = api

    def get_all_products(self, limit: int = 100) -> List[Dict]:
        """
        Получить все товары продавца с ценами.
        Использует актуальный метод POST /content/v2/get/cards/list.

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
        Поиск товаров по артикулу или названию.

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
        Получение товаров с ценами и скидками через Prices API.
        Использует метод GET /api/v2/list/goods/filter.

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
        Получение размеров товара с ценами.
        Использует метод GET /api/v2/list/goods/size/nm.

        Args:
            nm_id: Артикул товара (nmID)

        Returns:
            Список размеров с ценами
        """
        response = self.api.get(
            "/api/v2/list/goods/size/nm",
            params={"nmId": nm_id},
            base_url=API_ENDPOINTS["prices"]
        )
        return response.get("data", {}).get("listGoods", [])

    def update_price(self, nm_id: int, price: float, discount: Optional[int] = None) -> Dict:
        """
        Обновить цену товара.

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
            base_url=API_ENDPOINTS["prices"]
        )

    def update_multiple_prices(self, price_data: List[Dict]) -> Dict:
        """
        Массовое обновление цен.

        Args:
            price_data: Список словарей с nmID, price и discount
            Пример: [{"nmID": 123, "price": 1000, "discount": 10}, ...]

        Returns:
            Информация о задаче обновления
        """
        return self.api.post(
            "/api/v2/upload/task",
            data={"data": price_data},
            base_url=API_ENDPOINTS["prices"]
        )

    def get_quarantine_products(self) -> List[Dict]:
        """
        Получить товары в карантине (не обновлялись более 30 дней).

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
        Получить список категорий товаров.

        Returns:
            Список категорий
        """
        response = self.api.get(
            "/content/v2/object/parent/all",
            base_url=self.api.config.content_url
        )
        return response.get("data", [])

    def get_all_chrt_ids(self) -> List[int]:
        """
        Получить все chrtIds (ID размеров) товаров продавца.

        Returns:
            Список chrtIds для всех товаров
        """
        chrt_ids = []
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
                    logger.warning("Неожиданный ответ от Content API: %s", type(response))
                    break

                if 'error' in response and response.get('error'):
                    logger.error("Content API error: %s", response.get('errorText', 'Unknown error'))
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

            logger.info("Получено %d карточек, %d chrtIds", total_cards, len(chrt_ids))
            return chrt_ids

        except Exception as e:
            logger.error("Ошибка получения chrtIds: %s", e, exc_info=True)
            return []

    def get_products_with_photos_and_prices(self, limit: int = 100, search: str = None) -> List[Dict]:
        """
        Получить товары с фото, ценами и скидками.
        Объединяет данные из Content API (фото, название) и Prices API (цены, скидки).
        
        Args:
            limit: Лимит товаров (макс 100)
            search: Поисковый запрос
            
        Returns:
            Список товаров с полной информацией:
            - nmID: Артикул WB
            - vendorCode: Артикул продавца
            - title: Название товара
            - brand: Бренд
            - photo_url: URL фото товара
            - price: Цена без скидки
            - discountedPrice: Цена со скидкой
            - discount: Скидка в %
            - sizes: Размеры товара с ценами
        """
        try:
            # Шаг 1: Получаем товары с ценами из Prices API
            params = {"limit": limit, "offset": 0}
            if search:
                params["search"] = search

            prices_response = self.api.get(
                "/api/v2/list/goods/filter",
                params=params,
                base_url=API_ENDPOINTS["prices"]
            )
            
            goods = prices_response.get("data", {}).get("listGoods", [])
            if not goods:
                return []
            
            # Создаем словарь товаров по nmID для быстрого доступа
            goods_by_nm = {g['nmID']: g for g in goods}
            nm_ids = list(goods_by_nm.keys())
            
            # Шаг 2: Получаем детальную информацию о товарах из Content API (включая фото)
            content_data = []
            batch_size = 100
            
            for i in range(0, len(nm_ids), batch_size):
                batch = nm_ids[i:i + batch_size]
                response = self.api.post(
                    "/content/v2/get/cards/list",
                    data={
                        "settings": {
                            "cursor": {"limit": batch_size},
                            "filter": {
                                "nmID": batch,
                                "withPhoto": 1
                            }
                        }
                    },
                    base_url=API_ENDPOINTS["content"]
                )
                
                cards = response.get("cards", [])
                content_data.extend(cards)
            
            # Шаг 3: Объединяем данные из обоих API
            result = []
            for card in content_data:
                nm_id = card.get('nmID')
                if nm_id not in goods_by_nm:
                    continue
                    
                price_info = goods_by_nm[nm_id]
                
                # Получаем URL фото (берем первое фото, размер square 600x600)
                photos = card.get('photos', [])
                photo_url = None
                if photos:
                    photo_url = photos[0].get('square') or photos[0].get('c246x328') or photos[0].get('big')
                
                # Получаем информацию о ценах
                sizes = price_info.get('sizes', [])
                price = 0
                discounted_price = 0
                
                if sizes:
                    # Берем первый размер
                    first_size = sizes[0]
                    price = first_size.get('price', 0)
                    discounted_price = first_size.get('discountedPrice', price)
                
                result.append({
                    'nmID': nm_id,
                    'vendorCode': card.get('vendorCode', ''),
                    'title': card.get('title', ''),
                    'brand': card.get('brand', ''),
                    'subjectName': card.get('subjectName', ''),
                    'photo_url': photo_url,
                    'price': price,
                    'discountedPrice': discounted_price,
                    'discount': price_info.get('discount', 0),
                    'clubDiscount': price_info.get('clubDiscount', 0),
                    'currency': price_info.get('currencyIsoCode4217', 'RUB'),
                    'sizes': sizes,
                    'editableSizePrice': price_info.get('editableSizePrice', False)
                })
            
            return result
            
        except Exception as e:
            logger.error("Ошибка получения товаров с ценами и фото: %s", e, exc_info=True)
            return []

    def get_chrt_id_mapping(self) -> Dict[int, Dict]:
        """
        Получить соответствие chrtId → информация о товаре.

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
            logger.error("Ошибка получения chrtId mapping: %s", e)
            return {}
