"""
Tests for wb_client.py - WB API client functionality.
"""

import json
import time
from unittest.mock import Mock

import pytest

from wb_client import API_ENDPOINTS, RateLimiter, WBConfig, WildberriesAPI


class TestWBConfig:
    """Tests for WBConfig dataclass"""

    def test_default_values(self, mock_api_token):
        """Test default configuration values"""
        config = WBConfig(api_token=mock_api_token)
        assert config.api_token == mock_api_token
        assert config.base_url == "https://suppliers-api.wildberries.ru"
        assert config.content_url == "https://content-api.wildberries.ru"
        assert config.timeout == 30
        assert config.max_retries == 3

    def test_custom_values(self, mock_api_token):
        """Test custom configuration values"""
        config = WBConfig(api_token=mock_api_token, timeout=60, max_retries=5)
        assert config.timeout == 60
        assert config.max_retries == 5


class TestRateLimiter:
    """Tests for RateLimiter functionality"""

    def test_rate_limit_values(self):
        """Test that rate limits are properly defined"""
        limiter = RateLimiter()
        assert limiter.RATE_LIMITS["statistics"] == 60
        assert limiter.RATE_LIMITS["content"] == 100
        assert limiter.RATE_LIMITS["marketplace"] == 1000

    def test_wait_calculation(self):
        """Test wait time calculation between requests"""
        limiter = RateLimiter()

        start_time = time.time()
        limiter.wait_if_needed("content")
        limiter.wait_if_needed("content")
        elapsed = time.time() - start_time

        assert elapsed >= 0.5

    def test_no_wait_for_different_categories(self):
        """Test that different categories don't interfere"""
        limiter = RateLimiter()
        limiter.last_request_time["content"] = time.time()

        start_time = time.time()
        limiter.wait_if_needed("marketplace")
        elapsed = time.time() - start_time

        assert elapsed < 0.1


class TestWildberriesAPI:
    """Tests for WildberriesAPI class"""

    def test_initialization(self, wb_config):
        """Test API client initialization"""
        api = WildberriesAPI(wb_config)
        assert api.config == wb_config
        assert api.session is not None
        assert api.rate_limiter is not None

    def test_headers_set_correctly(self, wb_config):
        """Test that authorization headers are set"""
        api = WildberriesAPI(wb_config)
        assert api.session.headers["Authorization"] == wb_config.api_token
        assert api.session.headers["Content-Type"] == "application/json"
        assert api.session.headers["Accept"] == "application/json"

    def test_get_api_category(self, wb_config):
        """Test API category detection from URLs"""
        api = WildberriesAPI(wb_config)

        assert api._get_api_category("https://statistics-api.wildberries.ru") == "statistics"
        assert api._get_api_category("https://content-api.wildberries.ru") == "content"
        assert api._get_api_category("https://marketplace-api.wildberries.ru") == "marketplace"
        assert api._get_api_category("https://seller-analytics-api.wildberries.ru") == "analytics"
        assert api._get_api_category("https://discounts-prices-api.wildberries.ru") == "prices"
        assert api._get_api_category(None) == "default"

    def test_successful_get_request(self, mock_api_with_session, mock_response_success):
        """Test successful GET request"""
        mock_api_with_session.session.request.return_value = mock_response_success

        result = mock_api_with_session.get("/api/v1/test", base_url="https://test.wildberries.ru")

        assert result == {"success": True}
        mock_api_with_session.session.request.assert_called_once()

    def test_successful_post_request(self, mock_api_with_session, mock_response_success):
        """Test successful POST request"""
        mock_api_with_session.session.request.return_value = mock_response_success

        data = {"key": "value"}
        result = mock_api_with_session.post("/api/v1/test", data=data, base_url="https://test.wildberries.ru")

        assert result == {"success": True}
        call_args = mock_api_with_session.session.request.call_args
        assert call_args[1]["json"] == data

    def test_http_error_handling(self, mock_api_with_session, mock_response_404):
        """Test handling of HTTP 404 error"""
        mock_api_with_session.session.request.return_value = mock_response_404

        with pytest.raises(Exception) as exc_info:
            mock_api_with_session.get("/api/v1/nonexistent")

        assert "HTTP Error 404" in str(exc_info.value)

    def test_429_rate_limit_retry(self, mock_api_with_session, mock_response_429, mock_response_success):
        """Test retry on 429 Too Many Requests"""
        mock_api_with_session.session.request.side_effect = [mock_response_429, mock_response_success]

        mock_api_with_session._make_request("GET", "/api/v1/test", retry_count=0)

        assert mock_api_with_session.session.request.call_count == 2

    def test_timeout_error(self, mock_api_with_session):
        """Test handling of timeout error"""
        from requests.exceptions import Timeout

        mock_api_with_session.session.request.side_effect = Timeout("Request timed out")

        with pytest.raises(Exception) as exc_info:
            mock_api_with_session.get("/api/v1/test")

        assert "Timeout Error" in str(exc_info.value)

    def test_ssl_error_retry(self, mock_api_with_session):
        """Test retry on SSL error"""
        from requests.exceptions import SSLError

        mock_api_with_session.session.request.side_effect = SSLError("SSL error")

        with pytest.raises(Exception):
            mock_api_with_session._make_request("GET", "/api/v1/test", retry_count=0)

        assert mock_api_with_session.session.request.call_count > 1

    def test_empty_response(self, mock_api_with_session):
        """Test handling of empty response"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b""
        mock_response.raise_for_status.return_value = None
        mock_api_with_session.session.request.return_value = mock_response

        result = mock_api_with_session.get("/api/v1/test")

        assert result == {}

    def test_json_decode_error(self, mock_api_with_session):
        """Test handling of invalid JSON response"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b"invalid json"
        mock_response.json.side_effect = json.JSONDecodeError("test", "test", 0)
        mock_response.raise_for_status.return_value = None
        mock_response.text = "invalid json"
        mock_api_with_session.session.request.return_value = mock_response

        result = mock_api_with_session.get("/api/v1/test")

        assert result == {"raw_response": "invalid json"}

    def test_get_diagnostics_snapshot(self, wb_config):
        """Diagnostics should expose request/error counters."""
        api = WildberriesAPI(wb_config)
        snapshot = api.get_diagnostics()

        assert snapshot["total_requests"] == 0
        assert snapshot["total_errors"] == 0
        assert isinstance(snapshot["status_codes"], dict)

    def test_health_status_uses_ping(self, wb_config):
        """Health check should aggregate ping results for all key domains."""
        api = WildberriesAPI(wb_config)
        api.ping = Mock(return_value={"Status": "OK", "TS": "2026-02-26T10:00:00+03:00"})

        result = api.get_health_status()

        assert result["overall_ok"] is True
        assert set(result["checks"].keys()) == {
            "common",
            "content",
            "marketplace",
            "prices",
            "statistics",
            "advert",
            "analytics",
        }
        assert api.ping.call_count == 7


class TestAPIEndpoints:
    """Tests for API_ENDPOINTS configuration"""

    def test_all_endpoints_defined(self):
        """Test that all required endpoints are defined"""
        required_endpoints = ["statistics", "marketplace", "content", "advert", "analytics", "prices", "tariffs"]

        for endpoint in required_endpoints:
            assert endpoint in API_ENDPOINTS
            assert API_ENDPOINTS[endpoint].startswith("https://")

    def test_endpoint_urls_correct(self):
        """Test that endpoint URLs are correctly formatted"""
        assert "wildberries.ru" in API_ENDPOINTS["statistics"]
        assert "wildberries.ru" in API_ENDPOINTS["content"]
        assert "wildberries.ru" in API_ENDPOINTS["marketplace"]

