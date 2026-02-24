"""
Tests for managers.py - Business logic and analytics.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import json

from managers import ProductsManager, AnalyticsManager, AdvertisingManager, OrdersManager


class TestProductsManager:
    """Tests for ProductsManager"""
    
    def test_get_all_products_success(self, products_manager):
        """Test successful retrieval of all products"""
        mock_response = {
            "cards": [
                {
                    "nmID": 123456,
                    "title": "Test Product 1",
                    "vendorCode": "TEST-001",
                    "sizes": [{"price": 1000}]
                },
                {
                    "nmID": 123457,
                    "title": "Test Product 2",
                    "vendorCode": "TEST-002",
                    "sizes": [{"price": 2000}]
                }
            ]
        }
        products_manager.api.post.return_value = mock_response
        
        result = products_manager.get_all_products(limit=100)
        
        assert len(result) == 2
        assert result[0]["nmID"] == 123456
        assert result[1]["nmID"] == 123457
        products_manager.api.post.assert_called_once()
    
    def test_get_all_products_empty_response(self, products_manager):
        """Test handling of empty product list"""
        products_manager.api.post.return_value = {"cards": []}
        
        result = products_manager.get_all_products(limit=100)
        
        assert result == []
    
    def test_search_products(self, products_manager):
        """Test product search functionality"""
        mock_response = {
            "cards": [
                {
                    "nmID": 123456,
                    "title": "iPhone 15",
                    "vendorCode": "PHONE-001"
                }
            ]
        }
        products_manager.api.post.return_value = mock_response
        
        result = products_manager.search_products("iPhone", limit=10)
        
        assert len(result) == 1
        assert result[0]["title"] == "iPhone 15"
        # Check that search query was sent
        call_args = products_manager.api.post.call_args
        assert "iPhone" in str(call_args)
    
    def test_update_price_success(self, products_manager):
        """Test successful price update"""
        mock_response = {"uploadID": 12345}
        products_manager.api.post.return_value = mock_response
        
        result = products_manager.update_price(nm_id=123456, price=1500, discount=10)
        
        assert result["uploadID"] == 12345
        # Check that correct data was sent
        call_args = products_manager.api.post.call_args
        assert "nmID" in str(call_args)
        assert "1500" in str(call_args)
    
    def test_get_warehouses(self, products_manager):
        """Test warehouse retrieval"""
        mock_response = {
            "data": [
                {"id": 1, "name": "Warehouse 1"},
                {"id": 2, "name": "Warehouse 2"}
            ]
        }
        products_manager.api.get.return_value = mock_response
        
        result = products_manager.get_warehouses()
        
        assert len(result) == 2
        assert result[0]["id"] == 1


class TestAnalyticsManager:
    """Tests for AnalyticsManager"""
    
    def test_calculate_revenue_uses_forpay(self, analytics_manager, mock_sales_data):
        """Test that revenue calculation uses forPay field (not totalPrice)"""
        # Mock get_sales to return our test data
        analytics_manager.get_sales = Mock(return_value=mock_sales_data)
        
        result = analytics_manager.calculate_revenue(days=30)
        
        # Expected: 1000 + 2000 = 3000 (using forPay, not totalPrice)
        # Return (500) should not be counted in total_sales but should be in data
        assert result["total_revenue"] == 3000.00
        assert result["total_sales"] == 3  # 2 sales + 1 return
        assert result["average_check"] == 1000.00  # 3000 / 3
    
    def test_calculate_revenue_no_sales(self, analytics_manager):
        """Test revenue calculation when no sales exist"""
        analytics_manager.get_sales = Mock(return_value=[])
        
        result = analytics_manager.calculate_revenue(days=30)
        
        assert result["total_revenue"] == 0
        assert result["total_sales"] == 0
        assert result["average_check"] == 0
    
    def test_calculate_revenue_detailed(self, analytics_manager):
        """Test detailed revenue calculation with all deductions"""
        # Mock detailed report data
        mock_report = [
            {
                "retailAmount": 1000,
                "forPay": 800,
                "commissionAmount": 100,
                "deliveryAmount": 50,
                "storageFee": 10,
                "penalty": 0,
                "isReturn": False,
                "isCancel": False
            },
            {
                "retailAmount": 500,
                "forPay": 400,
                "commissionAmount": 50,
                "deliveryAmount": 30,
                "storageFee": 5,
                "penalty": 0,
                "isReturn": True,
                "isCancel": False
            }
        ]
        analytics_manager.get_detailed_report = Mock(return_value=mock_report)
        
        result = analytics_manager.calculate_revenue_detailed(days=30)
        
        assert result["total_revenue"] == 1000  # Only sales (not returns)
        assert result["total_returns"] == 500  # Return amount
        assert result["net_revenue"] == 1200  # 800 + 400
        assert result["total_commission"] == 150  # 100 + 50
        assert result["total_logistics"] == 80  # 50 + 30
        assert result["total_storage"] == 15  # 10 + 5
        assert result["total_sales"] == 1
        assert result["total_returns_count"] == 1
        assert result["return_rate"] == 50.0  # 1 return out of 2 operations
    
    def test_get_sales_caching(self, analytics_manager, mock_sales_data):
        """Test that sales data is cached"""
        analytics_manager.api.get = Mock(return_value=mock_sales_data)
        
        # First call - should hit API
        result1 = analytics_manager.get_sales(date_from="2026-02-01")
        assert analytics_manager.api.get.call_count == 1
        
        # Second call - should use cache
        result2 = analytics_manager.get_sales(date_from="2026-02-01")
        assert analytics_manager.api.get.call_count == 1  # No additional API call
        
        assert result1 == result2
    
    def test_clear_cache(self, analytics_manager, mock_sales_data):
        """Test cache clearing functionality"""
        analytics_manager.api.get = Mock(return_value=mock_sales_data)
        
        # Populate cache
        analytics_manager.get_sales(date_from="2026-02-01")
        assert len(analytics_manager._cache) > 0
        
        # Clear cache
        analytics_manager.clear_cache()
        assert len(analytics_manager._cache) == 0
    
    def test_get_top_products(self, analytics_manager):
        """Test top products calculation"""
        mock_sales = [
            {"nmId": 1, "subject": "Phone", "forPay": 1000, "isCancel": False},
            {"nmId": 1, "subject": "Phone", "forPay": 1000, "isCancel": False},
            {"nmId": 2, "subject": "Case", "forPay": 500, "isCancel": False},
            {"nmId": 1, "subject": "Phone", "forPay": 1000, "isCancel": True},  # Return
        ]
        analytics_manager.get_sales = Mock(return_value=mock_sales)
        
        result = analytics_manager.get_top_products(days=30, limit=10)
        
        assert len(result) == 2  # Two unique products
        assert result[0]["nm_id"] == 1  # Phone should be first (2000 revenue)
        assert result[0]["revenue"] == 2000.0  # Excludes return
        assert result[0]["quantity"] == 3  # Includes return for count
        assert result[1]["nm_id"] == 2  # Case should be second


class TestAdvertisingManager:
    """Tests for AdvertisingManager"""
    
    def test_get_campaigns_success(self, advertising_manager):
        """Test successful retrieval of campaigns"""
        mock_response = {
            "adverts": [
                {"advertId": 1, "name": "Campaign 1", "status": 7},
                {"advertId": 2, "name": "Campaign 2", "status": 11}
            ]
        }
        advertising_manager.api.get.return_value = mock_response
        
        result = advertising_manager.get_campaigns()
        
        assert len(result) == 2
        assert result[0]["advertId"] == 1
        assert result[1]["advertId"] == 2
    
    def test_get_campaigns_with_status_filter(self, advertising_manager):
        """Test campaign filtering by status"""
        mock_response = {
            "adverts": [
                {"advertId": 1, "name": "Active", "status": 7}
            ]
        }
        advertising_manager.api.get.return_value = mock_response
        
        result = advertising_manager.get_campaigns(status=7)
        
        # Check that status parameter was passed
        call_args = advertising_manager.api.get.call_args
        assert "status" in str(call_args) or call_args[1].get("params", {}).get("status") == 7
    
    def test_get_campaign_stats(self, advertising_manager):
        """Test campaign statistics retrieval"""
        mock_response = [
            {"advertId": 1, "clicks": 100, "ctr": 2.5, "cpm": 150}
        ]
        advertising_manager.api.get.return_value = mock_response
        
        result = advertising_manager.get_campaign_stats([1, 2, 3])
        
        assert len(result) == 1
        assert result[0]["clicks"] == 100
    
    def test_start_campaign_success(self, advertising_manager):
        """Test successful campaign start"""
        advertising_manager.api.get.return_value = {}
        
        result = advertising_manager.start_campaign(12345)
        
        assert result is True
        # Verify correct endpoint was called
        call_args = advertising_manager.api.get.call_args
        assert "/adv/v0/start" in str(call_args)
    
    def test_start_campaign_failure(self, advertising_manager):
        """Test campaign start failure"""
        advertising_manager.api.get.side_effect = Exception("API Error")
        
        result = advertising_manager.start_campaign(12345)
        
        assert result is False
    
    def test_pause_campaign(self, advertising_manager):
        """Test campaign pause"""
        advertising_manager.api.get.return_value = {}
        
        result = advertising_manager.pause_campaign(12345)
        
        assert result is True
    
    def test_update_bid_success(self, advertising_manager):
        """Test successful bid update"""
        advertising_manager.api.patch.return_value = {}
        
        result = advertising_manager.update_bid([1, 2, 3], 150)
        
        assert result is True
        # Verify correct data was sent
        call_args = advertising_manager.api.patch.call_args
        assert "150" in str(call_args)
    
    def test_get_budget(self, advertising_manager):
        """Test budget retrieval"""
        mock_response = {
            "budget": 1000.50,
            "total": 5000.00
        }
        advertising_manager.api.get.return_value = mock_response
        
        result = advertising_manager.get_budget(12345)
        
        assert result["budget"] == 1000.50
        assert result["total"] == 5000.00


class TestOrdersManager:
    """Tests for OrdersManager"""
    
    def test_get_new_orders_success(self, orders_manager):
        """Test successful retrieval of new orders"""
        mock_response = {
            "orders": [
                {"id": 1, "status": "new", "total": 1000},
                {"id": 2, "status": "new", "total": 2000}
            ]
        }
        orders_manager.api.get.return_value = mock_response
        
        result = orders_manager.get_new_orders(limit=100)
        
        assert len(result) == 2
        assert result[0]["id"] == 1
    
    def test_get_new_orders_empty(self, orders_manager):
        """Test handling of no new orders"""
        orders_manager.api.get.return_value = {"orders": []}
        
        result = orders_manager.get_new_orders(limit=100)
        
        assert result == []
    
    def test_confirm_assembly_success(self, orders_manager):
        """Test successful order assembly confirmation"""
        orders_manager.api.patch.return_value = {}
        
        result = orders_manager.confirm_assembly(12345)
        
        assert result is True
    
    def test_confirm_assembly_failure(self, orders_manager):
        """Test assembly confirmation failure"""
        orders_manager.api.patch.side_effect = Exception("API Error")
        
        result = orders_manager.confirm_assembly(12345)
        
        assert result is False
    
    def test_cancel_order_success(self, orders_manager):
        """Test successful order cancellation"""
        orders_manager.api.patch.return_value = {}
        
        result = orders_manager.cancel_order(12345, "Нет в наличии")
        
        assert result is True
    
    def test_cancel_order_failure(self, orders_manager):
        """Test order cancellation failure"""
        orders_manager.api.patch.side_effect = Exception("API Error")
        
        result = orders_manager.cancel_order(12345)
        
        assert result is False
