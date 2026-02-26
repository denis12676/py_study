import json
import logging
import threading
import time
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Dict, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


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


class WBAPIError(Exception):
    """Ошибка запроса к WB API."""

    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


class RateLimiter:
    """Rate limiter для контроля частоты запросов к API"""

    # Rate limits для разных категорий API (запросов/мин)
    # Примечание: Statistics API имеет лимит 1 запрос/мин, но мы не делаем
    # preemptive задержку, а полагаемся на retry при 429 ошибке
    RATE_LIMITS = {
        "statistics": 60,  # 60 req/min = 1 req/sec - разумный лимит без искусственных задержек
        "content": 100,  # 100 req/min = 1 req/0.6s
        "marketplace": 1000,  # 1000 req/min = 1 req/0.06s
        "advert": 300,  # 300 req/min
        "analytics": 100,  # 100 req/min
        "prices": 100,  # 100 req/min
        "default": 100,
    }

    def __init__(self):
        self.last_request_time = defaultdict(float)
        self.lock = threading.Lock()

    def wait_if_needed(self, category: str = "default"):
        """Ждет если нужно, чтобы не превысить rate limit"""
        with self.lock:
            limit = self.RATE_LIMITS.get(category, self.RATE_LIMITS["default"])
            min_interval = 60.0 / limit

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

        # Простая runtime-диагностика для мониторинга качества интеграции.
        self._diagnostics: Dict[str, Any] = {
            "started_at": time.time(),
            "total_requests": 0,
            "total_errors": 0,
            "status_codes": defaultdict(int),
            "last_error": None,
        }

        retry_strategy = Retry(
            total=config.max_retries,
            backoff_factor=2,
            status_forcelist=[500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS", "POST", "PUT", "DELETE", "PATCH"],
        )

        adapter = HTTPAdapter(max_retries=retry_strategy, pool_maxsize=10)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

        self.session.headers.update(
            {
                "Authorization": config.api_token,
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "WB-AI-Agent/1.0",
            }
        )

    def _record_response(self, status_code: int, is_error: bool = False, error_text: Optional[str] = None) -> None:
        self._diagnostics["total_requests"] += 1
        self._diagnostics["status_codes"][str(status_code)] += 1
        if is_error:
            self._diagnostics["total_errors"] += 1
            self._diagnostics["last_error"] = error_text

    def _record_exception(self, message: str) -> None:
        self._diagnostics["total_requests"] += 1
        self._diagnostics["total_errors"] += 1
        self._diagnostics["status_codes"]["exception"] += 1
        self._diagnostics["last_error"] = message

    def get_diagnostics(self) -> Dict[str, Any]:
        """Возвращает снапшот метрик клиента для локального мониторинга."""
        status_codes = dict(self._diagnostics["status_codes"])
        uptime_seconds = int(time.time() - self._diagnostics["started_at"])
        return {
            "uptime_seconds": uptime_seconds,
            "total_requests": self._diagnostics["total_requests"],
            "total_errors": self._diagnostics["total_errors"],
            "status_codes": status_codes,
            "last_error": self._diagnostics["last_error"],
        }

    def _get_api_category(self, base_url: Optional[str]) -> str:
        """Определяет категорию API по базовому URL"""
        if not base_url:
            return "default"

        url_lower = base_url.lower()

        if "statistics-api" in url_lower:
            return "statistics"
        if "content-api" in url_lower:
            return "content"
        if "marketplace-api" in url_lower:
            return "marketplace"
        if "advert-api" in url_lower:
            return "advert"
        if "seller-analytics-api" in url_lower or "analytics-api" in url_lower:
            return "analytics"
        if "discounts-prices-api" in url_lower:
            return "prices"
        if "supplies-api" in url_lower:
            return "content"
        if "common-api" in url_lower:
            return "default"
        return "default"

    def _make_request(
        self,
        method: str,
        url: str,
        params: Optional[Dict] = None,
        data: Optional[Dict] = None,
        base_url: Optional[str] = None,
        retry_count: int = 0,
    ) -> Any:
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
            Ответ API в виде dict/list/primitive
        """
        full_url = f"{base_url or self.config.base_url}{url}"
        category = self._get_api_category(base_url)

        self.rate_limiter.wait_if_needed(category)

        response = None
        try:
            response = self.session.request(
                method=method,
                url=full_url,
                params=params,
                json=data if data else None,
                timeout=self.config.timeout,
            )
            response.raise_for_status()
            self._record_response(response.status_code)

            if response.content:
                try:
                    return response.json()
                except json.JSONDecodeError:
                    return {"raw_response": response.text}
            return {}

        except requests.exceptions.HTTPError as exc:
            http_response = getattr(exc, "response", None) or response
            status_code = http_response.status_code if http_response is not None else 0

            if status_code == 429:
                retry_after = (http_response.headers or {}).get("X-Ratelimit-Retry") if http_response is not None else None
                try:
                    sleep_time = int(retry_after) if retry_after else 10 * (2**retry_count)
                except ValueError:
                    sleep_time = 10 * (2**retry_count)

                if retry_count < self.config.max_retries:
                    logger.warning(
                        "Rate limit 429 for %s %s. Sleep %ss then retry %s/%s",
                        method,
                        full_url,
                        sleep_time,
                        retry_count + 1,
                        self.config.max_retries,
                    )
                    self._record_response(status_code, is_error=True, error_text="429 Too Many Requests")
                    time.sleep(sleep_time)
                    return self._make_request(method, url, params, data, base_url, retry_count + 1)

                limit_reset = (http_response.headers or {}).get("X-Ratelimit-Reset", "неизвестно") if http_response is not None else "неизвестно"
                message = f"Слишком много запросов к API. Попробуйте снова через {limit_reset} секунд."
                self._record_response(status_code, is_error=True, error_text=message)
                raise WBAPIError(message, status_code=status_code)

            response_text = http_response.text if http_response is not None else str(exc)
            message = f"HTTP Error {status_code}: {response_text}"
            self._record_response(status_code, is_error=True, error_text=message)
            raise WBAPIError(message, status_code=status_code)

        except requests.exceptions.SSLError as exc:
            if retry_count < self.config.max_retries:
                time.sleep(2**retry_count)
                return self._make_request(method, url, params, data, base_url, retry_count + 1)
            message = f"SSL Error: {exc}. Попробуйте позже или проверьте подключение."
            self._record_exception(message)
            raise WBAPIError(message)

        except requests.exceptions.ConnectionError as exc:
            if retry_count < self.config.max_retries:
                time.sleep(2**retry_count)
                return self._make_request(method, url, params, data, base_url, retry_count + 1)
            message = f"Connection Error: {exc}. Проверьте интернет-соединение."
            self._record_exception(message)
            raise WBAPIError(message)

        except requests.exceptions.Timeout:
            message = "Timeout Error: Запрос занял слишком много времени. Попробуйте увеличить timeout."
            self._record_exception(message)
            raise WBAPIError(message)

        except requests.exceptions.RequestException as exc:
            message = f"Request failed: {exc}"
            self._record_exception(message)
            raise WBAPIError(message)

    def get(self, url: str, params: Optional[Dict] = None, base_url: Optional[str] = None) -> Any:
        """GET запрос"""
        return self._make_request("GET", url, params=params, base_url=base_url)

    def post(
        self, url: str, data: Optional[Dict] = None, params: Optional[Dict] = None, base_url: Optional[str] = None
    ) -> Any:
        """POST запрос"""
        return self._make_request("POST", url, params=params, data=data, base_url=base_url)

    def put(self, url: str, data: Optional[Dict] = None, base_url: Optional[str] = None) -> Any:
        """PUT запрос"""
        return self._make_request("PUT", url, data=data, base_url=base_url)

    def delete(self, url: str, params: Optional[Dict] = None, base_url: Optional[str] = None) -> Any:
        """DELETE запрос"""
        return self._make_request("DELETE", url, params=params, base_url=base_url)

    def patch(self, url: str, data: Optional[Dict] = None, base_url: Optional[str] = None) -> Any:
        """PATCH запрос"""
        return self._make_request("PATCH", url, data=data, base_url=base_url)

    def ping(self, base_url: Optional[str] = None) -> Dict[str, Any]:
        """Проверка подключения к конкретному сервису WB через GET /ping."""
        response = self.get("/ping", base_url=base_url or API_ENDPOINTS["tariffs"])
        if isinstance(response, dict):
            return response
        return {"Status": "UNKNOWN", "raw": response}

    def get_health_status(self) -> Dict[str, Any]:
        """Проверяет доступность ключевых доменов WB через /ping (см. 01-general.yaml)."""
        checks: Dict[str, Any] = {}
        endpoint_map = {
            "common": API_ENDPOINTS["tariffs"],
            "content": API_ENDPOINTS["content"],
            "marketplace": API_ENDPOINTS["marketplace"],
            "prices": API_ENDPOINTS["prices"],
            "statistics": API_ENDPOINTS["statistics"],
            "advert": API_ENDPOINTS["advert"],
            "analytics": API_ENDPOINTS["analytics"],
        }

        for name, base_url in endpoint_map.items():
            try:
                ping_response = self.ping(base_url=base_url)
                checks[name] = {
                    "ok": str(ping_response.get("Status", "")).upper() == "OK",
                    "status": ping_response.get("Status", "UNKNOWN"),
                    "ts": ping_response.get("TS"),
                }
            except Exception as exc:
                checks[name] = {"ok": False, "error": str(exc)}

        diagnostics = self.get_diagnostics()
        return {
            "overall_ok": all(item.get("ok", False) for item in checks.values()),
            "checks": checks,
            "diagnostics": diagnostics,
        }


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
    "prices": "https://discounts-prices-api.wildberries.ru",
    "questions": "https://questions-api.wildberries.ru",
    "returns": "https://returns-api.wildberries.ru",
    "tariffs": "https://common-api.wildberries.ru",
}

