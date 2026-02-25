import requests
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
import json
import time
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from collections import defaultdict
import threading


@dataclass
class WBConfig:
    """Конфигурация для Wildberries API"""
    api_token: str
    base_url: str = "https://suppliers-api.wildberries.ru"
    content_url: str = "https://content-api.wildberries.ru"
    marketplace_url: str = "https://marketplace-api.wildberries.ru"
    advert_url: str = "https://advert-api.wb.ru"
    statistics_url: str = "https://statistics-api.wildberries.ru"
    timeout: int = 30
    max_retries: int = 3


class RateLimiter:
    """Rate limiter для контроля частоты запросов к API"""
    
    # Rate limits для разных категорий API (запросов/мин)
    # Примечание: Statistics API имеет лимит 1 запрос/мин, но мы не делаем 
    # preemptive задержку, а полагаемся на retry при 429 ошибке
    RATE_LIMITS = {
        "statistics": 60,     # 60 req/min = 1 req/sec - разумный лимит без искусственных задержек
        "content": 100,       # 100 req/min = 1 req/0.6s
        "marketplace": 1000,  # 1000 req/min = 1 req/0.06s
        "advert": 300,        # 300 req/min
        "analytics": 100,     # 100 req/min
        "prices": 100,        # 100 req/min
        "default": 100
    }
    
    def __init__(self):
        self.last_request_time = defaultdict(float)
        self.lock = threading.Lock()
    
    def wait_if_needed(self, category: str = "default"):
        """Ждет если нужно, чтобы не превысить rate limit"""
        with self.lock:
            limit = self.RATE_LIMITS.get(category, self.RATE_LIMITS["default"])
            min_interval = 60.0 / limit  # минимальный интервал между запросами в секундах
            
            last_time = self.last_request_time[category]
            current_time = time.time()
            elapsed = current_time - last_time
            
            if elapsed < min_interval:
                sleep_time = min_interval - elapsed
                time.sleep(sleep_time)
            
            self.last_request_time[category] = time.time()


class WildberriesAPI:
    """
    Базовый клиент для Wildberries API.
    
    Документация: https://dev.wildberries.ru/
    """
    
    def __init__(self, config: WBConfig):
        self.config = config
        self.rate_limiter = RateLimiter()
        self.session = requests.Session()
        
        # Настраиваем retry strategy (не для 429 - их обрабатываем отдельно с rate limiter)
        retry_strategy = Retry(
            total=config.max_retries,
            backoff_factor=2,  # Увеличили для более долгих пауз
            status_forcelist=[500, 502, 503, 504],  # Убрали 429
            allowed_methods=["HEAD", "GET", "OPTIONS", "POST", "PUT", "DELETE", "PATCH"]
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy, pool_maxsize=10)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)
        
        self.session.headers.update({
            "Authorization": config.api_token,
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "WB-AI-Agent/1.0"
        })
    
    def _get_api_category(self, base_url: Optional[str]) -> str:
        """Определяет категорию API по базовому URL"""
        if not base_url:
            return "default"
        
        url_lower = base_url.lower()
        
        if "statistics-api" in url_lower:
            return "statistics"
        elif "content-api" in url_lower:
            return "content"
        elif "marketplace-api" in url_lower:
            return "marketplace"
        elif "advert-api" in url_lower:
            return "advert"
        elif "seller-analytics-api" in url_lower or "analytics-api" in url_lower:
            return "analytics"
        elif "discounts-prices-api" in url_lower:
            return "prices"
        elif "supplies-api" in url_lower:
            return "content"  # supplies использует content rate limits
        elif "common-api" in url_lower:
            return "default"
        else:
            return "default"
    
    def _make_request(
        self, 
        method: str, 
        url: str, 
        params: Optional[Dict] = None, 
        data: Optional[Dict] = None,
        base_url: Optional[str] = None,
        retry_count: int = 0
    ) -> Dict[str, Any]:
        """
        Выполняет HTTP запрос к API
        
        Args:
            method: HTTP метод (GET, POST, PUT, DELETE, PATCH)
            url: Endpoint URL
            params: Query параметры
            data: Тело запроса
            base_url: Базовый URL (если отличается от стандартного)
            retry_count: Текущий номер попытки
        
        Returns:
            Dict с ответом API
        """
        full_url = f"{base_url or self.config.base_url}{url}"
        
        # Определяем категорию API для rate limiting
        category = self._get_api_category(base_url)
        
        # Применяем rate limiting
        self.rate_limiter.wait_if_needed(category)
        
        try:
            response = self.session.request(
                method=method,
                url=full_url,
                params=params,
                json=data if data else None,
                timeout=self.config.timeout
            )
            
            response.raise_for_status()
            
            # Проверяем, есть ли контент в ответе
            if response.content:
                return response.json()
            return {}
            
        except requests.exceptions.HTTPError as e:
            # Обрабатываем 429 Too Many Requests
            if e.response.status_code == 429:
                # Пытаемся получить время ожидания из заголовков
                retry_after = e.response.headers.get('X-Ratelimit-Retry')
                if retry_after:
                    sleep_time = int(retry_after)
                else:
                    # Экспоненциальная задержка: 10, 20, 40 секунд
                    sleep_time = 10 * (2 ** retry_count)
                
                if retry_count < self.config.max_retries:
                    print(f"⚠️  Rate limit exceeded. Waiting {sleep_time} seconds before retry {retry_count + 1}/{self.config.max_retries}...")
                    time.sleep(sleep_time)
                    return self._make_request(method, url, params, data, base_url, retry_count + 1)
                
                # Если все попытки исчерпаны, показываем сколько ждать
                limit_reset = e.response.headers.get('X-Ratelimit-Reset', 'неизвестно')
                raise Exception(f"Слишком много запросов к API. Попробуйте снова через {limit_reset} секунд.")
            
            error_msg = f"HTTP Error {e.response.status_code}: {e.response.text}"
            raise Exception(error_msg)
        except requests.exceptions.SSLError as e:
            # При SSL ошибке пробуем еще раз с задержкой
            if retry_count < self.config.max_retries:
                time.sleep(2 ** retry_count)  # Экспоненциальная задержка
                return self._make_request(method, url, params, data, base_url, retry_count + 1)
            raise Exception(f"SSL Error: {str(e)}. Попробуйте позже или проверьте подключение.")
        except requests.exceptions.ConnectionError as e:
            # При ошибке соединения пробуем еще раз
            if retry_count < self.config.max_retries:
                time.sleep(2 ** retry_count)
                return self._make_request(method, url, params, data, base_url, retry_count + 1)
            raise Exception(f"Connection Error: {str(e)}. Проверьте интернет-соединение.")
        except requests.exceptions.Timeout as e:
            raise Exception(f"Timeout Error: Запрос занял слишком много времени. Попробуйте увеличить timeout.")
        except requests.exceptions.RequestException as e:
            raise Exception(f"Request failed: {str(e)}")
        except json.JSONDecodeError:
            return {"raw_response": response.text}
    
    def get(self, url: str, params: Optional[Dict] = None, base_url: Optional[str] = None) -> Dict:
        """GET запрос"""
        return self._make_request("GET", url, params=params, base_url=base_url)
    
    def post(self, url: str, data: Optional[Dict] = None, params: Optional[Dict] = None, base_url: Optional[str] = None) -> Dict:
        """POST запрос"""
        return self._make_request("POST", url, params=params, data=data, base_url=base_url)
    
    def put(self, url: str, data: Optional[Dict] = None, base_url: Optional[str] = None) -> Dict:
        """PUT запрос"""
        return self._make_request("PUT", url, data=data, base_url=base_url)
    
    def delete(self, url: str, params: Optional[Dict] = None, base_url: Optional[str] = None) -> Dict:
        """DELETE запрос"""
        return self._make_request("DELETE", url, params=params, base_url=base_url)
    
    def patch(self, url: str, data: Optional[Dict] = None, base_url: Optional[str] = None) -> Dict:
        """PATCH запрос"""
        return self._make_request("PATCH", url, data=data, base_url=base_url)


# Доступные базовые URL для разных категорий API
API_ENDPOINTS = {
    "statistics": "https://statistics-api.wildberries.ru",
    "marketplace": "https://marketplace-api.wildberries.ru", 
    "content": "https://content-api.wildberries.ru",
    "advert": "https://advert-api.wb.ru",
    "supplies": "https://supplies-api.wildberries.ru",
    "recommendations": "https://recommendations-api.wildberries.ru",
    "feedbacks": "https://feedbacks-api.wildberries.ru",
    "analytics": "https://seller-analytics-api.wildberries.ru",
    "prices": "https://discounts-prices-api.wildberries.ru",  # Отдельный API для цен
    "questions": "https://questions-api.wildberries.ru",
    "returns": "https://returns-api.wildberries.ru",
    "tariffs": "https://common-api.wildberries.ru",
}
