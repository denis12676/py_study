from typing import Any, Dict, List


class RequestAnalyzer:
    INTENT_MAP: List[Dict] = [
        {
            "triggers": ["товар", "продукт", "карточка", "артикул", "nm", "позиция"],
            "default": "list_products",
            "type": "products",
            "subtypes": [
                {"action": "update_price",    "triggers": ["цена", "стоимость", "измени", "обнови", "повысь", "понизь", "дороже", "дешевле"]},
                {"action": "search_products", "triggers": ["поиск", "найди", "где"]},
                {"action": "check_stocks",    "triggers": ["остаток", "наличие", "склад", "карантин"]},
                {"action": "list_products",   "triggers": ["все", "список", "покажи", "выведи", "каталог"]},
            ],
        },
        {
            "triggers": ["продажа", "выручка", "заказ", "аналитик", "статистик", "отчет", "деньг", "доход"],
            "default": "sales_report",
            "type": "analytics",
            "subtypes": [
                {"action": "weekly_report",   "triggers": ["недел", "weekly"]},
                {"action": "top_products",    "triggers": ["топ", "лучш", "популярн", "рейтинг"]},
                {"action": "revenue_report",  "triggers": ["выручка", "доход", "оборот", "деньг"]},
                {"action": "detailed_report", "triggers": ["детальн", "подробн", "комиссия", "себестоимость", "прибыль"]},
            ],
        },
        {
            "triggers": ["реклам", "кампани", "продвижение", "ставка", "cpc", "cpm", "бюджет"],
            "default": "list_campaigns",
            "type": "advertising",
            "subtypes": [
                {"action": "start_campaign",  "triggers": ["запусти", "стартуй", "включи", "начни"]},
                {"action": "pause_campaign",  "triggers": ["останови", "пауза", "выключи", "приостанови"]},
                {"action": "delete_campaign", "triggers": ["удали", "убери", "очисти"]},
                {"action": "create_campaign", "triggers": ["создай", "новая", "добавь"]},
                {"action": "update_bid",      "triggers": ["ставка", "цена клика"]},
                {"action": "campaign_stats",  "triggers": ["статистик", "эффективность", "roi"]},
            ],
        },
        {
            "triggers": ["заказ", "сборка", "отгрузка", "fbs", "отмена"],
            "default": "list_orders",
            "type": "orders",
            "subtypes": [
                {"action": "new_orders",   "triggers": ["новый", "новые", "текущий", "собрать", "подтверди"]},
                {"action": "cancel_order", "triggers": ["отмени", "отмена", "отменить"]},
            ],
        },
        {
            "triggers": ["отзыв", "вопрос", "рейтинг", "оценка", "комментарий"],
            "default": "list_feedbacks",
            "type": "communication",
            "subtypes": [],
        },
        {
            "triggers": ["магазин", "продавец", "информация", "профиль", "кто я"],
            "default": "seller_info",
            "type": "general",
            "subtypes": [],
        },
    ]

    def analyze(self, query: str) -> Dict[str, Any]:
        q = query.lower()
        for intent in self.INTENT_MAP:
            if any(w in q for w in intent["triggers"]):
                for sub in intent["subtypes"]:
                    if any(w in q for w in sub["triggers"]):
                        return {"action": sub["action"], "type": intent["type"]}
                return {"action": intent["default"], "type": intent["type"]}
        return {"action": "help", "type": "general"}
