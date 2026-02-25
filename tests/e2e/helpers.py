"""
Helper functions for E2E tests with Wildberries API and Streamlit dashboard.
"""

import os
import time
from typing import Optional
from playwright.sync_api import Page, expect


def get_api_token_from_env() -> Optional[str]:
    """Get API token from .env file or environment variable."""
    # Try environment variable first
    token = os.environ.get('WB_API_TOKEN')
    if token:
        return token
    
    # Try .env file
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env')
    if os.path.exists(env_path):
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.startswith('WB_API_TOKEN='):
                    return line.strip().split('=', 1)[1].strip('"\'')
    
    return None


def get_product_price_api(vendor_code: str, api_token: Optional[str] = None) -> int:
    """
    Get current product price via API.
    
    Args:
        vendor_code: Vendor code of the product (e.g., "LM-10160")
        api_token: WB API token (if not provided, will read from .env)
    
    Returns:
        Current price as integer
    
    Raises:
        ValueError: If API token not found
        RuntimeError: If API request fails
    """
    import requests
    
    if not api_token:
        api_token = get_api_token_from_env()
    
    if not api_token:
        raise ValueError("API token not found. Please set WB_API_TOKEN in .env file or environment variable.")
    
    headers = {
        "Authorization": api_token,
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "WB-E2E-Test/1.0"
    }
    
    # Search for product by vendor code using prices API
    url = "https://discounts-prices-api.wildberries.ru/api/v2/list/goods/filter"
    params = {"limit": 100, "offset": 0, "search": vendor_code}
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        goods = data.get("data", {}).get("listGoods", [])
        
        for product in goods:
            if product.get("vendorCode") == vendor_code:
                sizes = product.get("sizes", [])
                if sizes:
                    return int(sizes[0].get("price", 0))
        
        # If not found via vendor code, try content API
        content_url = "https://content-api.wildberries.ru/content/v2/get/cards/list"
        payload = {
            "settings": {
                "cursor": {"limit": 100},
                "filter": {"textSearch": vendor_code, "withPhoto": -1}
            }
        }
        
        response = requests.post(content_url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        
        cards = response.json().get("cards", [])
        for card in cards:
            if card.get("vendorCode") == vendor_code:
                sizes = card.get("sizes", [])
                if sizes:
                    price = sizes[0].get("price", 0)
                    if price:
                        return int(price)
        
        raise RuntimeError(f"Product with vendor code '{vendor_code}' not found or has no price")
        
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"API request failed: {e}")


def update_price_api(vendor_code: str, price: int, discount: int = 0, api_token: Optional[str] = None) -> dict:
    """
    Update product price via API.
    
    Args:
        vendor_code: Vendor code of the product (e.g., "LM-10160")
        price: New price value
        discount: Discount percentage (default 0)
        api_token: WB API token (if not provided, will read from .env)
    
    Returns:
        API response as dictionary
    
    Raises:
        ValueError: If API token not found
        RuntimeError: If API request fails
    """
    import requests
    
    if not api_token:
        api_token = get_api_token_from_env()
    
    if not api_token:
        raise ValueError("API token not found. Please set WB_API_TOKEN in .env file or environment variable.")
    
    headers = {
        "Authorization": api_token,
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "WB-E2E-Test/1.0"
    }
    
    # First, get nmID for the vendor code
    content_url = "https://content-api.wildberries.ru/content/v2/get/cards/list"
    payload = {
        "settings": {
            "cursor": {"limit": 100},
            "filter": {"textSearch": vendor_code, "withPhoto": -1}
        }
    }
    
    try:
        response = requests.post(content_url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        
        cards = response.json().get("cards", [])
        nm_id = None
        for card in cards:
            if card.get("vendorCode") == vendor_code:
                nm_id = card.get("nmID")
                break
        
        if not nm_id:
            raise RuntimeError(f"Product with vendor code '{vendor_code}' not found")
        
        # Ensure nm_id is integer
        nm_id = int(nm_id)
        
        # Update price using prices API
        update_url = "https://discounts-prices-api.wildberries.ru/api/v2/upload/task"
        update_data = {
            "data": [{
                "nmID": nm_id,
                "price": int(price)
            }]
        }
        
        if discount > 0:
            update_data["data"][0]["discount"] = int(discount)
        
        print(f"   DEBUG: Sending price update request: {update_data}")
        
        response = requests.post(update_url, headers=headers, json=update_data, timeout=30)
        
        print(f"   DEBUG: Response status: {response.status_code}")
        print(f"   DEBUG: Response body: {response.text[:500]}")
        
        response.raise_for_status()
        
        return response.json()
        
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"API request failed: {e}")


def search_product_in_dashboard(page: Page, vendor_code: str, timeout: int = 30) -> bool:
    """
    Search for a product in the dashboard and wait for results to load.
    
    Args:
        page: Playwright page object
        vendor_code: Vendor code to search for
        timeout: Maximum wait time in seconds
    
    Returns:
        True if products were found, False otherwise
    """
    # Clear and enter search query
    search_input = page.get_by_placeholder("Введите запрос...")
    
    # Clear existing text
    search_input.clear()
    
    # Type the search query
    search_input.fill(vendor_code)
    
    # Click "Load" button to trigger search
    load_button = page.get_by_role("button", name="🔄 Загрузить")
    load_button.click()
    
    # Wait for loading spinner to appear and disappear
    # First check for spinner (if loading is fast, it might skip)
    try:
        spinner = page.locator("[data-testid='stSpinner']")
        if spinner.count() > 0:
            spinner.wait_for(state="hidden", timeout=timeout * 1000)
    except:
        pass  # Spinner might not appear or disappear too quickly
    
    # Wait for products to load by checking for checkboxes
    try:
        # Look for any checkbox with pattern chk_*
        checkboxes = page.locator("input[id*='chk_']")
        checkboxes.first.wait_for(state="visible", timeout=timeout * 1000)
        return checkboxes.count() > 0
    except:
        # Check if "No products" message appears
        no_products = page.locator("text=Товары не найдены")
        if no_products.count() > 0 and no_products.is_visible():
            return False
        
        # Try alternative check - look for product rows
        product_rows = page.locator(".price-table-row")
        return product_rows.count() > 0


def wait_for_streamlit_app(page: Page, timeout: int = 30) -> None:
    """
    Wait for Streamlit app to be fully loaded.
    
    Args:
        page: Playwright page object
        timeout: Maximum wait time in seconds
    """
    # Wait for main app container
    page.wait_for_selector("[data-testid='stAppViewContainer']", timeout=timeout * 1000)
    
    # Wait for sidebar
    page.wait_for_selector("[data-testid='stSidebar']", timeout=timeout * 1000)


def take_screenshot_on_failure(page: Page, test_name: str, output_dir: str = "tests/e2e/screenshots") -> str:
    """
    Take a screenshot when test fails.
    
    Args:
        page: Playwright page object
        test_name: Name of the test
        output_dir: Directory to save screenshots
    
    Returns:
        Path to saved screenshot
    """
    import os
    from datetime import datetime
    
    os.makedirs(output_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{test_name}_failure_{timestamp}.png"
    filepath = os.path.join(output_dir, filename)
    
    page.screenshot(path=filepath, full_page=True)
    return filepath


def calculate_discount(price: int, discounted_price: int) -> int:
    """
    Calculate discount percentage.
    
    Args:
        price: Original price
        discounted_price: Price with discount
    
    Returns:
        Discount percentage (0-100)
    """
    if price <= 0 or discounted_price >= price:
        return 0
    
    return int((1 - discounted_price / price) * 100)
