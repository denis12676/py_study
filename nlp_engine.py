import re
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta

class RequestAnalyzer:
    """Анализатор запросов на естественном языке с извлечением сущностей."""
    
    INTENT_MAP = [
        # ... (triggers remains same for brevity, but I'll optimize the search logic)
    ]

    def __init__(self):
        # Переиспользуем существующую карту интентов
        from nlp_engine import RequestAnalyzer as OldAnalyzer
        self.INTENT_MAP = OldAnalyzer.INTENT_MAP

    def analyze(self, query: str) -> Dict[str, Any]:
        """
        Анализирует запрос и извлекает намерение и параметры.
        """
        q = query.lower()
        result = {"action": "help", "type": "general", "params": {}}

        # 1. Определяем намерение (Intent)
        found_intent = False
        for intent in self.INTENT_MAP:
            if any(w in q for w in intent["triggers"]):
                found_intent = True
                result["type"] = intent["type"]
                result["action"] = intent["default"]
                
                for sub in intent["subtypes"]:
                    if any(w in q for w in sub["triggers"]):
                        result["action"] = sub["action"]
                        break
                break
        
        # 2. Извлекаем параметры (Entities)
        result["params"] = self._extract_entities(q, result["action"])
        
        return result

    def _extract_entities(self, q: str, action: str) -> Dict[str, Any]:
        params = {}
        
        # Извлекаем все числа
        numbers = re.findall(r'\d+', q)
        
        # Артикулы (обычно 7-10 цифр)
        nm_ids = [int(n) for n in numbers if 6 <= len(n) <= 12]
        if nm_ids:
            params["nm_id"] = nm_ids[0]
            params["nm_ids"] = nm_ids

        # Цены и ставки (обычно 2-5 цифр, идут после слов "цена", "ставка", "на")
        if any(word in q for word in ["цена", "ставка", "на", "за"]):
            small_numbers = [int(n) for n in numbers if len(n) < 6]
            if small_numbers:
                params["value"] = small_numbers[-1] # Берем последнее число как значение

        # Даты и периоды
        if "недел" in q:
            params["days"] = 7
        elif "месяц" in q:
            params["days"] = 30
        elif "сегодня" in q:
            params["days"] = 1
        elif "вчера" in q:
            params["days"] = 2
            
        return params
