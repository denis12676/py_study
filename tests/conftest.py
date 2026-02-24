"""
Pytest configuration and fixtures for Wildberries AI Agent tests.
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timedelta

# Add parent directory to path
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from wb_client import WildberriesAPI, WBConfig, API_ENDPOINTS
from managers import ProductsManager, AnalyticsManager, AdvertisingManager, OrdersManager
from ai_agent import WildberriesAIAgent


@pytest.fixture
def mock_api_token():
    """Mock API token for testing"""
    return "eyJhbGciOiJFUzI1NiIsImtpZCI6IjIwMjQxMTI3djEiLCJ0eXAiOiJKV1QifQ.test"


@pytest.fixture
def wb_config(mock_api_token):
    """WBConfig instance for testing"""
    return WBConfig(
        api_token=mock_api_token,
        timeout=5,
        max_retries=1
    )


@pytest.fixture
def mock_api(wb_config):
    """Mocked WildberriesAPI instance with mockable methods"""
    api = Mock(spec=WildberriesAPI)
    api.config = wb_config
    
    # Mock all HTTP methods
    api.get = Mock()
    api.post = Mock()
    api.put = Mock()
    api.delete = Mock()
    api.patch = Mock()
    
    # Mock rate limiter
    api.rate_limiter = Mock()
    api._get_api_category = Mock(return_value="default")
    
    yield api


@pytest.fixture
def mock_api_with_session(wb_config):
    """Mocked WildberriesAPI with session (for advanced tests)"""
    with patch('wb_client.requests.Session') as mock_session:
        api = WildberriesAPI(wb_config)
        api.session = mock_session.return_value
        yield api


@pytest.fixture
def products_manager(mock_api):
    """ProductsManager instance with mocked API"""
    return ProductsManager(mock_api)


@pytest.fixture
def analytics_manager(mock_api):
    """AnalyticsManager instance with mocked API"""
    return AnalyticsManager(mock_api)


@pytest.fixture
def advertising_manager(mock_api):
    """AdvertisingManager instance with mocked API"""
    return AdvertisingManager(mock_api)


@pytest.fixture
def orders_manager(mock_api):
    """OrdersManager instance with mocked API"""
    return OrdersManager(mock_api)


@pytest.fixture
def sample_product():
    """Sample product data"""
    return {
        "nmID": 123456,
        "title": "Test Product",
        "vendorCode": "TEST-001",
        "brand": "TestBrand",
        "subjectName": "Electronics",
        "sizes": [
            {
                "sizeName": "One Size",
                "price": 1500,
                "skus": ["1234567890"]
            }
        ]
    }


@pytest.fixture
def sample_sale():
    """Sample sale data"""
    return {
        "date": "2026-02-20T10:30:00",
        "lastChangeDate": "2026-02-20T10:30:00",
        "warehouseName": "Koledino",
        "supplierArticle": "TEST-001",
        "nmId": 123456,
        "barcode": "1234567890123",
        "category": "Electronics",
        "subject": "Smartphones",
        "brand": "TestBrand",
        "techSize": "One Size",
        "incomeID": 12345,
        "isSupply": False,
        "isRealization": True,
        "totalPrice": 2000,
        "discountPercent": 10,
        "spp": 5,
        "forPay": 1710.00,
        "finishedPrice": 1800,
        "priceWithDisc": 1800,
        "saleID": "S123456789",
        "sticker": "STICKER123",
        "gNumber": "12345678901234567890",
        "srid": "abc123.def456.789"
    }


@pytest.fixture
def sample_campaign():
    """Sample advertising campaign data"""
    return {
        "advertId": 12345,
        "name": "Test Campaign",
        "status": 7,  # Active
        "type": 6,  # Search
        "cpm": 100,
        "nmIds": [123456, 123457]
    }


@pytest.fixture
def mock_response_success():
    """Mock successful API response"""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"success": True}
    mock_response.content = b'{"success": true}'
    mock_response.raise_for_status.return_value = None
    return mock_response


@pytest.fixture
def mock_response_404():
    """Mock 404 API response"""
    from requests.exceptions import HTTPError
    mock_response = Mock()
    mock_response.status_code = 404
    mock_response.json.return_value = {"error": "Not found"}
    mock_response.content = b'{"error": "Not found"}'
    mock_response.raise_for_status.side_effect = HTTPError("404 Client Error")
    return mock_response


@pytest.fixture
def mock_response_429():
    """Mock 429 Rate Limit API response"""
    from requests.exceptions import HTTPError
    mock_response = Mock()
    mock_response.status_code = 429
    mock_response.headers = {
        'X-Ratelimit-Retry': '5',
        'X-Ratelimit-Reset': '30',
        'X-Ratelimit-Limit': '10'
    }
    mock_response.json.return_value = {"error": "Too Many Requests"}
    mock_response.content = b'{"error": "Too Many Requests"}'
    mock_response.raise_for_status.side_effect = HTTPError("429 Too Many Requests")
    return mock_response


@pytest.fixture
def date_range_30_days():
    """Date range for last 30 days"""
    end = datetime.now()
    start = end - timedelta(days=30)
    return {
        "date_from": start.strftime("%Y-%m-%d"),
        "date_to": end.strftime("%Y-%m-%d"),
        "days": 30
    }


@pytest.fixture
def mock_sales_data():
    """Mock sales data for testing revenue calculation"""
    return [
        {
            "date": "2026-02-01T10:00:00",
            "nmId": 1,
            "forPay": 1000.00,
            "totalPrice": 1200.00,
            "isCancel": False
        },
        {
            "date": "2026-02-02T11:00:00",
            "nmId": 2,
            "forPay": 2000.00,
            "totalPrice": 2500.00,
            "isCancel": False
        },
        {
            "date": "2026-02-03T12:00:00",
            "nmId": 1,
            "forPay": 500.00,
            "totalPrice": 600.00,
            "isCancel": True  # Return
        }
    ]


# Hook to print test summary
def pytest_terminal_summary(terminalreporter, exitstatus, config):
    """Print test summary at the end"""
    if terminalreporter.stats.get('passed'):
        passed = len(terminalreporter.stats['passed'])
        print(f"\n[OK] {passed} tests passed")
    
    if terminalreporter.stats.get('failed'):
        failed = len(terminalreporter.stats['failed'])
        print(f"\n[FAIL] {failed} tests failed")
    
    if terminalreporter.stats.get('error'):
        errors = len(terminalreporter.stats['error'])
        print(f"\n[ERROR] {errors} errors")


# Configure pytest
def pytest_configure(config):
    """Configure pytest markers"""
    config.addinivalue_line("markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')")
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line("markers", "unit: marks tests as unit tests")
