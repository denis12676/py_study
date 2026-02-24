"""
Tests for ai_agent.py - Natural language processing and command routing.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from ai_agent import WildberriesAIAgent


class TestAIAgentInitialization:
    """Tests for AI Agent initialization"""
    
    def test_initialization_success(self):
        """Test successful agent initialization"""
        with patch('ai_agent.WildberriesAPI') as mock_api_class:
            with patch('ai_agent.WBConfig') as mock_config:
                mock_api = Mock()
                mock_api_class.return_value = mock_api
                
                agent = WildberriesAIAgent("test_token")
                
                assert agent.api == mock_api
                assert agent.products is not None
                assert agent.analytics is not None
                assert agent.orders is not None
                assert agent.advertising is not None
                assert agent.last_result is None
    
    def test_initialization_with_connection_test(self):
        """Test that connection is tested on initialization"""
        with patch('ai_agent.WildberriesAPI') as mock_api_class:
            mock_api = Mock()
            mock_api.get.return_value = {"name": "Test Seller"}
            mock_api_class.return_value = mock_api
            
            agent = WildberriesAIAgent("test_token")
            
            # Connection test should have been called
            mock_api.get.assert_called_once()


class TestRequestAnalysis:
    """Tests for natural language request analysis"""
    
    @pytest.fixture
    def agent(self):
        """Create mocked agent for testing"""
        with patch('ai_agent.WildberriesAPI'):
            with patch('ai_agent.WBConfig'):
                agent = WildberriesAIAgent("test_token")
                # Mock all managers
                agent.products = Mock()
                agent.analytics = Mock()
                agent.orders = Mock()
                agent.advertising = Mock()
                return agent
    
    # Products tests
    def test_analyze_list_products(self, agent):
        """Test 'show all products' command recognition"""
        queries = [
            "покажи все товары",
            "выведи список товаров",
            "каталог товаров"
        ]
        for query in queries:
            result = agent._analyze_request(query)
            assert result["action"] == "list_products", f"Failed for: {query}"
            assert result["type"] == "products"
    
    def test_analyze_search_products(self, agent):
        """Test product search command recognition"""
        queries = [
            "найди товар iPhone",
            "поиск товара",
            "где товар 12345"
        ]
        for query in queries:
            result = agent._analyze_request(query)
            assert result["action"] == "search_products", f"Failed for: {query}"
    
    def test_analyze_update_price(self, agent):
        """Test price update command recognition"""
        queries = [
            "обнови цену товара 12345 на 1500",
            "измени цену 12345",
            "повысь цену"
        ]
        for query in queries:
            result = agent._analyze_request(query)
            assert result["action"] == "update_price", f"Failed for: {query}"
    
    # Analytics tests
    def test_analyze_revenue_report(self, agent):
        """Test revenue report command recognition"""
        queries = [
            "какая выручка за 30 дней",
            "доход за неделю",
            "сколько денег заработано"
        ]
        for query in queries:
            result = agent._analyze_request(query)
            assert result["action"] == "revenue_report", f"Failed for: {query}"
    
    def test_analyze_weekly_report(self, agent):
        """Test weekly report command recognition"""
        queries = [
            "еженедельный отчет",
            "отчет за неделю",
            "продажи за прошлую неделю"
        ]
        for query in queries:
            result = agent._analyze_request(query)
            assert result["action"] == "weekly_report", f"Failed for: {query}"
    
    def test_analyze_top_products(self, agent):
        """Test top products command recognition"""
        queries = [
            "топ 10 товаров",
            "лучшие продажи",
            "популярные товары"
        ]
        for query in queries:
            result = agent._analyze_request(query)
            assert result["action"] == "top_products", f"Failed for: {query}"
    
    def test_analyze_detailed_report(self, agent):
        """Test detailed report command recognition"""
        queries = [
            "детальный отчет",
            "подробная статистика",
            "комиссия и прибыль"
        ]
        for query in queries:
            result = agent._analyze_request(query)
            assert result["action"] == "detailed_report", f"Failed for: {query}"
    
    # Advertising tests
    def test_analyze_list_campaigns(self, agent):
        """Test campaigns list command recognition"""
        queries = [
            "покажи рекламные кампании",
            "список кампаний",
            "вся реклама"
        ]
        for query in queries:
            result = agent._analyze_request(query)
            assert result["action"] == "list_campaigns", f"Failed for: {query}"
    
    def test_analyze_start_campaign(self, agent):
        """Test campaign start command recognition"""
        queries = [
            "запусти кампанию 12345",
            "включи рекламу 12345",
            "начни кампанию"
        ]
        for query in queries:
            result = agent._analyze_request(query)
            assert result["action"] == "start_campaign", f"Failed for: {query}"
    
    def test_analyze_pause_campaign(self, agent):
        """Test campaign pause command recognition"""
        queries = [
            "останови кампанию 12345",
            "поставь на паузу 12345",
            "выключи рекламу"
        ]
        for query in queries:
            result = agent._analyze_request(query)
            assert result["action"] == "pause_campaign", f"Failed for: {query}"
    
    # Orders tests
    def test_analyze_new_orders(self, agent):
        """Test new orders command recognition"""
        queries = [
            "новые заказы",
            "заказы для сборки",
            "покажи заказы"
        ]
        for query in queries:
            result = agent._analyze_request(query)
            assert result["action"] == "new_orders", f"Failed for: {query}"
    
    # General tests
    def test_analyze_seller_info(self, agent):
        """Test seller info command recognition"""
        queries = [
            "информация о магазине",
            "данные продавца",
            "кто я"
        ]
        for query in queries:
            result = agent._analyze_request(query)
            assert result["action"] == "seller_info", f"Failed for: {query}"
    
    def test_analyze_help(self, agent):
        """Test help command recognition (fallback)"""
        queries = [
            "что ты умеешь",
            "помощь",
            "как пользоваться"
        ]
        for query in queries:
            result = agent._analyze_request(query)
            assert result["action"] == "help", f"Failed for: {query}"


class TestParameterExtraction:
    """Tests for parameter extraction from queries"""
    
    @pytest.fixture
    def agent(self):
        """Create mocked agent for testing"""
        with patch('ai_agent.WildberriesAPI'):
            with patch('ai_agent.WBConfig'):
                return WildberriesAIAgent("test_token")
    
    def test_extract_price_params(self, agent):
        """Test extraction of price update parameters"""
        params = agent._extract_params("Обнови цену товара 12345 на 1500 рублей", "update_price")
        assert params["nm_id"] == 12345
        assert params["price"] == 1500
    
    def test_extract_price_with_discount(self, agent):
        """Test extraction of price and discount"""
        params = agent._extract_params("Обнови цену 12345 на 2000 со скидкой 15%", "update_price")
        assert params["nm_id"] == 12345
        assert params["price"] == 2000
        assert params["discount"] == 15
    
    def test_extract_search_query(self, agent):
        """Test extraction of search query"""
        params = agent._extract_params("Найди товар iPhone 15 Pro", "search_products")
        assert params["query"] == "iPhone 15 Pro"
    
    def test_extract_campaign_id(self, agent):
        """Test extraction of campaign ID"""
        params = agent._extract_params("Запусти кампанию 67890", "start_campaign")
        assert params["campaign_id"] == 67890
    
    def test_extract_bid(self, agent):
        """Test extraction of bid amount"""
        params = agent._extract_params("Измени ставку 12345 на 100", "update_bid")
        assert params["campaign_id"] == 12345
        assert params["bid"] == 100
    
    def test_extract_days(self, agent):
        """Test extraction of days parameter"""
        params = agent._extract_params("Выручка за 7 дней", "revenue_report")
        assert params["days"] == 7
        
        params = agent._extract_params("Выручка за неделю", "revenue_report")
        assert params["days"] == 7
        
        params = agent._extract_params("Выручка за месяц", "revenue_report")
        assert params["days"] == 30


class TestActionExecution:
    """Tests for action execution"""
    
    @pytest.fixture
    def agent(self):
        """Create mocked agent for testing"""
        with patch('ai_agent.WildberriesAPI'):
            with patch('ai_agent.WBConfig'):
                agent = WildberriesAIAgent("test_token")
                # Mock all managers with specific return values
                agent.products = Mock()
                agent.products.get_all_products.return_value = []
                agent.products.search_products.return_value = []
                agent.products.update_price.return_value = {"success": True}
                
                agent.analytics = Mock()
                agent.analytics.get_sales.return_value = []
                agent.analytics.calculate_revenue.return_value = {"total_revenue": 1000}
                agent.analytics.get_weekly_sales_report.return_value = {"week_start": "2026-02-01"}
                agent.analytics.get_top_products.return_value = []
                agent.analytics.get_detailed_report.return_value = []
                
                agent.advertising = Mock()
                agent.advertising.get_campaigns.return_value = []
                agent.advertising.start_campaign.return_value = True
                agent.advertising.pause_campaign.return_value = True
                
                agent.orders = Mock()
                agent.orders.get_new_orders.return_value = []
                agent.orders.confirm_assembly.return_value = True
                
                return agent
    
    def test_execute_list_products(self, agent):
        """Test execution of list products action"""
        result = agent._execute_action("list_products", {})
        agent.products.get_all_products.assert_called_once()
        assert result == []
    
    def test_execute_update_price(self, agent):
        """Test execution of price update action"""
        params = {"nm_id": 123, "price": 1000, "discount": 10}
        result = agent._execute_action("update_price", params)
        agent.products.update_price.assert_called_with(nm_id=123, price=1000, discount=10)
        assert result["success"] is True
    
    def test_execute_revenue_report(self, agent):
        """Test execution of revenue report action"""
        params = {"days": 30}
        result = agent._execute_action("revenue_report", params)
        agent.analytics.calculate_revenue.assert_called_with(days=30)
        assert result["total_revenue"] == 1000
    
    def test_execute_weekly_report(self, agent):
        """Test execution of weekly report action"""
        params = {}
        result = agent._execute_action("weekly_report", params)
        agent.analytics.get_weekly_sales_report.assert_called_with(week_start=None)
        assert result["week_start"] == "2026-02-01"
    
    def test_execute_start_campaign(self, agent):
        """Test execution of start campaign action"""
        params = {"campaign_id": 12345}
        result = agent._execute_action("start_campaign", params)
        agent.advertising.start_campaign.assert_called_with(12345)
        assert result["success"] is True
    
    def test_execute_missing_params(self, agent):
        """Test execution with missing required parameters"""
        with pytest.raises(ValueError) as exc_info:
            agent._execute_action("update_price", {})  # Missing nm_id and price
        assert "Укажите артикул" in str(exc_info.value)
    
    def test_execute_unknown_action(self, agent):
        """Test execution of unknown action"""
        result = agent._execute_action("unknown_action", {})
        assert "error" in result


class TestFullExecution:
    """Integration-like tests for full execute() method"""
    
    def test_execute_full_flow_list_products(self):
        """Test full execution flow for list products"""
        with patch('ai_agent.WildberriesAPI'):
            with patch('ai_agent.WBConfig'):
                agent = WildberriesAIAgent("test_token")
                agent.products.get_all_products = Mock(return_value=[
                    {"nmID": 1, "title": "Product 1"}
                ])
                
                result = agent.execute("покажи все товары")
                
                assert result is not None
                agent.products.get_all_products.assert_called_once()
                assert agent.last_result is not None
    
    def test_execute_with_error_handling(self):
        """Test error handling during execution"""
        with patch('ai_agent.WildberriesAPI'):
            with patch('ai_agent.WBConfig'):
                agent = WildberriesAIAgent("test_token")
                agent.analytics.calculate_revenue = Mock(side_effect=Exception("API Error"))
                
                result = agent.execute("выручка за 30 дней")
                
                assert result is None


class TestHelp:
    """Tests for help functionality"""
    
    def test_get_help_returns_string(self):
        """Test that get_help returns help text"""
        with patch('ai_agent.WildberriesAPI'):
            with patch('ai_agent.WBConfig'):
                agent = WildberriesAIAgent("test_token")
                help_text = agent.get_help()
                
                assert isinstance(help_text, str)
                assert len(help_text) > 0
                assert "Wildberries AI Agent" in help_text
