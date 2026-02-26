"""
ProductsManager — управление товарами. Асинхронная версия.
"""

import logging
import asyncio
from typing import Dict, Any, List, Optional
from wb_client import WildberriesAPI, API_ENDPOINTS
from models import Product

logger = logging.getLogger(__name__)

class ProductsManager:
    def __init__(self, api: WildberriesAPI):
        self.api = api

    async def get_all_products_async(self, limit: int = 100) -> List[Product]:
        """Асинхронное получение всех товаров"""
        response = await self.api.apost(
            "/content/v2/get/cards/list",
            data={"settings": {"cursor": {"limit": limit}, "filter": {"withPhoto": -1}}},
            base_url=API_ENDPOINTS["content"]
        )
        cards = response.get("cards", [])
        return [Product.model_validate(card) for card in cards]

    async def get_products_with_photos_and_prices_async(self, limit: int = 100, search: str = None) -> List[Product]:
        """
        Ультра-быстрое получение товаров с фото и ценами (параллельные запросы).
        """
        try:
            # 1. Получаем цены (синхронно, так как это один запрос)
            params = {"limit": limit, "offset": 0}
            if search: params["search"] = search
            
            prices_resp = await self.api.aget("/api/v2/list/goods/filter", params=params, base_url=API_ENDPOINTS["prices"])
            goods = prices_resp.get("data", {}).get("listGoods", [])
            if not goods: return []
            
            goods_by_nm = {g['nmID']: g for g in goods}
            nm_ids = list(goods_by_nm.keys())
            
            # 2. Получаем контент батчами ПАРАЛЛЕЛЬНО
            batch_size = 100
            tasks = []
            for i in range(0, len(nm_ids), batch_size):
                batch = nm_ids[i:i + batch_size]
                tasks.append(self.api.apost(
                    "/content/v2/get/cards/list",
                    data={"settings": {"cursor": {"limit": batch_size}, "filter": {"nmID": batch, "withPhoto": -1}}},
                    base_url=API_ENDPOINTS["content"]
                ))
            
            # Запускаем все запросы одновременно!
            content_responses = await asyncio.gather(*tasks)
            
            content_data = []
            for resp in content_responses:
                content_data.extend(resp.get("cards", []))
            
            # 3. Сборка моделей
            result = []
            for card in content_data:
                nm_id = card.get('nmID')
                if nm_id not in goods_by_nm: continue
                
                price_info = goods_by_nm[nm_id]
                photos = card.get('photos', [])
                photo_url = photos[0].get('square') if photos else None
                
                product = Product.model_validate(card)
                product.photo_url = photo_url
                
                # Маппинг цен
                prices_by_chrt = {s['chrtID']: s for s in price_info.get('sizes', [])}
                for size_model in product.sizes:
                    if size_model.chrt_id in prices_by_chrt:
                        p_size = prices_by_chrt[size_model.chrt_id]
                        size_model.price = p_size.get('price', 0)
                        size_model.discount = price_info.get('discount', 0)
                        size_model.discounted_price = p_size.get('discountedPrice', size_model.price)
                
                result.append(product)
            
            return result
            
        except Exception as e:
            logger.error(f"Async enrichment error: {e}", exc_info=True)
            return []

    # Синхронные методы (заглушки для обратной совместимости)
    def get_all_products(self, limit: int = 100) -> List[Product]:
        return asyncio.run(self.get_all_products_async(limit))
    
    def update_price(self, nm_id: int, price: float, discount: Optional[int] = None) -> Dict:
        # Для простых POST запросов оставим пока синхронную реализацию в клиенте
        return self.api.post("/api/v2/upload/task", data={"data": [{"nmID": nm_id, "price": int(price), "discount": discount}]}, base_url=API_ENDPOINTS["prices"])

    def get_chrt_id_mapping(self) -> Dict[int, Dict]:
        # Вспомогательный метод, пока оставим как есть
        return {} 
