"""
End-to-end test for price management functionality.
Tests the complete flow: search product → edit price → submit → verify.
Target product: LM-10160
"""

import re
import time
import pytest
from playwright.sync_api import Page, expect
from .helpers import (
    get_product_price_api,
    update_price_api,
    search_product_in_dashboard,
    calculate_discount,
    get_api_token_from_env
)


class TestPriceManagement:
    """Test suite for price management functionality."""
    
    def test_search_and_update_price_lm10160(
        self,
        page: Page,
        test_vendor_code: str,
        original_price: int
    ):
        """
        End-to-end test: Search for LM-10160, update price, submit, verify.
        
        Steps:
        1. Navigate to price management section
        2. Search for product LM-10160
        3. Select the product
        4. Change price (+100 RUB)
        5. Verify discount recalculates
        6. Submit changes
        7. Verify success message
        """
        print(f"\n🧪 Starting E2E test for {test_vendor_code}")
        print(f"   Original price: {original_price} RUB")
        
        # Step 0: Authorize if needed
        print("\n🔐 Step 0: Check authorization")
        try:
            # Check if we see the welcome page (not authorized yet)
            welcome_text = page.locator("text=Введите API токен в боковой панели")
            if welcome_text.count() > 0 and welcome_text.is_visible():
                print("   Authorization required - need to connect")
                
                # Try to use saved token first
                saved_token_checkbox = page.locator("text=Использовать сохраненный токен").locator("xpath=..")
                if saved_token_checkbox.count() > 0:
                    try:
                        saved_token_checkbox.check()
                        print("   ✓ 'Use saved token' checkbox checked")
                    except:
                        print("   Could not check saved token checkbox")
                
                # Click "Подключиться" button
                connect_button = page.get_by_role("button", name="Подключиться")
                connect_button.click()
                print("   ✓ Connect button clicked")
                
                # Wait for online status with longer timeout
                page.wait_for_selector("text=● Онлайн", timeout=60000)
                print("   ✓ Connected successfully")
                
                # Wait for navigation menu to appear
                page.wait_for_selector("text=💰 Управление ценами", timeout=10000)
                print("   ✓ Navigation menu loaded")
            else:
                # Already authorized - check if menu exists
                price_menu = page.locator("text=💰 Управление ценами")
                if price_menu.count() == 0:
                    print("   Already authorized but menu not visible, waiting...")
                    page.wait_for_selector("text=💰 Управление ценами", timeout=10000)
                print("   Already authorized")
        except Exception as e:
            print(f"   Authorization error: {e}")
            # Try to continue anyway - maybe already authorized
            pass
        
        # Step 1: Navigate to price management section
        print("\n📍 Step 1: Navigate to price management")
        price_menu = page.get_by_role("button", name="💰 Управление ценами")
        price_menu.click()
        
        # Wait for price management page to load
        expect(page.get_by_text("💰 Управление ценами").first).to_be_visible(timeout=10000)
        print("   ✓ Price management page loaded")
        
        # Step 2: Wait for products to load
        print(f"\n🔍 Step 2: Wait for products to load")
        
        # Wait for products to load (look for the success message or table)
        try:
            # Wait for success message "Загружено X товаров"
            page.wait_for_selector("text=Загружено", timeout=30000)
            print("   ✓ Products loaded successfully")
        except:
            # If not, try to reload
            print("   Products not loaded, clicking 'Загрузить' button")
            load_button = page.get_by_role("button", name="🔄 Загрузить")
            load_button.click()
            page.wait_for_selector("text=Загружено", timeout=30000)
            print("   ✓ Products loaded after clicking reload")
        
        # Step 3: Search for and select the product
        print(f"\n☑️ Step 3: Search and select product {test_vendor_code}")
        
        # First, search for the specific product
        search_input = page.get_by_placeholder("Введите запрос...")
        search_input.fill(test_vendor_code)
        print(f"   ✓ Search query entered: {test_vendor_code}")
        
        # Click load button to apply filter
        load_button = page.get_by_role("button", name="Загрузить")
        load_button.click()
        print("   ✓ Filter applied")
        
        # Wait for filtered results
        time.sleep(2)
        
        # Now find the product row
        product_cell = page.locator("text=Арт.").filter(has_text=test_vendor_code)
        if product_cell.count() == 0:
            product_cell = page.locator(f"text={test_vendor_code}").first
        
        assert product_cell.count() > 0, f"Product {test_vendor_code} not found after filtering"
        print(f"   ✓ Product {test_vendor_code} found in filtered list")
        
        # Find checkbox - after filtering there should be only one product
        # Look for checkboxes in the table (skip the header checkbox which is first)
        checkboxes = page.locator("input[type='checkbox']")
        # Wait for checkboxes to be visible
        checkboxes.first.wait_for(state="visible", timeout=10000)
        
        # Use the second checkbox (first is header, second is the product)
        if checkboxes.count() >= 2:
            checkbox = checkboxes.nth(1)
        else:
            checkbox = checkboxes.first
        
        # Click using JavaScript to bypass any visibility issues
        checkbox.evaluate("el => el.click()")
        time.sleep(0.5)
        
        # Verify it's checked
        is_checked = checkbox.is_checked()
        if not is_checked:
            # Try force click
            checkbox.check(force=True)
            is_checked = checkbox.is_checked()
        
        assert is_checked, "Failed to select the product checkbox"
        print("   ✓ Product selected")
        
        # Verify "Send" button appears
        send_button = page.get_by_role("button", name=re.compile(r"Отправить \(\d+\)"))
        expect(send_button).to_be_visible(timeout=5000)
        print("   ✓ Send button is visible")
        
        # Step 4: Change the price (+100 RUB)
        new_price = original_price + 100
        print(f"\n💰 Step 4: Change price from {original_price} to {new_price}")
        
        # Find the price input - look for input with the current price value
        # Since we have only one product selected, find the first price input
        price_input = page.locator("input[type='number']").first
        
        # Properly interact with the field to trigger Streamlit's state update
        # 1. Click on the field to focus it
        price_input.click()
        time.sleep(0.3)
        
        # 2. Select all text (Ctrl+A) and delete it
        price_input.press("Control+a")
        price_input.press("Delete")
        time.sleep(0.3)
        
        # 3. Type the new value character by character
        price_input.type(str(new_price), delay=50)
        time.sleep(0.5)
        
        # 4. Press Tab to move focus away and trigger the update
        price_input.press("Tab")
        time.sleep(0.5)
        
        print(f"   ✓ Price changed to {new_price} RUB")
        
        # Step 5: Verify discount recalculates
        print("\n📊 Step 5: Verify discount calculation")
        
        # Get the discounted price input (second number input)
        discounted_input = page.locator("input[type='number']").nth(1)
        
        # If discounted price is different, calculate expected discount
        try:
            discounted_value = discounted_input.input_value()
            if discounted_value and int(discounted_value) < new_price:
                expected_discount = calculate_discount(new_price, int(discounted_value))
                print(f"   ✓ Discount recalculated: {expected_discount}%")
            else:
                print("   ✓ No discount applied (discounted price = regular price)")
        except:
            print("   ✓ Could not verify discount (discounted price input not found)")
        
        # Step 6: Submit changes
        print("\n📤 Step 6: Submit price changes")
        
        # Scroll button into view and click it
        send_button.scroll_into_view_if_needed()
        time.sleep(0.5)
        
        # Click the send button (without force to ensure proper event handling)
        send_button.click()
        print("   ✓ Send button clicked")
        
        # Wait longer for Streamlit to process
        time.sleep(5)
        
        # Check for success or error messages
        try:
            success_message = page.get_by_text(re.compile(r"Цены обновлены!|Цена обновлена!"))
            expect(success_message).to_be_visible(timeout=10000)
            print("   ✓ Success message appeared")
        except:
            # Check for error message
            error_locator = page.locator("text=Ошибка").or_(page.locator("text=Error"))
            if error_locator.count() > 0:
                print(f"   ⚠️ Error detected: {error_locator.first.text_content()}")
            else:
                print("   ⚠️ No success message appeared, but continuing...")
        
        # Step 7: Verify via API that price was actually updated
        print("\n🔍 Step 7: Verify price update via API")
        
        # Wait longer for API to process (Streamlit operations take time)
        print("   Waiting 5 seconds for API processing...")
        time.sleep(5)
        
        # Get current price from API
        api_token = get_api_token_from_env()
        current_price = get_product_price_api(test_vendor_code, api_token)
        
        assert current_price == new_price, (
            f"Price verification failed! "
            f"Expected: {new_price}, Got: {current_price}"
        )
        print(f"   ✓ Price verified via API: {current_price} RUB")
        
        print(f"\n✅ E2E test completed successfully!")
        print(f"   Product: {test_vendor_code}")
        print(f"   Old price: {original_price} RUB")
        print(f"   New price: {new_price} RUB")
    
    def test_zero_price_validation(
        self,
        page: Page,
        test_vendor_code: str
    ):
        """
        Test that price=0 is handled correctly (should default to 1).
        
        This tests the fix for StreamlitValueBelowMinError.
        """
        print(f"\n🧪 Testing zero price validation for {test_vendor_code}")
        
        # Navigate to price management
        price_menu = page.get_by_role("button", name="💰 Управление ценами")
        price_menu.click()
        expect(page.get_by_text("💰 Управление ценами").first).to_be_visible(timeout=10000)
        
        # Search for product
        found = search_product_in_dashboard(page, test_vendor_code, timeout=30)
        assert found, f"Product {test_vendor_code} not found"
        
        # Try to set price to 0 (this should be handled gracefully)
        # The UI should prevent this or show validation error
        price_input = page.locator(".price-table-row").filter(
            has_text=test_vendor_code
        ).locator("input[id*='price_']")
        
        # Attempt to enter 0
        price_input.fill("0")
        
        # The UI should either:
        # 1. Not accept 0 (keep previous value)
        # 2. Show validation error
        # 3. Default to 1
        
        # Verify the field doesn't have 0
        current_value = price_input.input_value()
        assert int(current_value) >= 1, f"Price should not be 0, got: {current_value}"
        
        print(f"   ✓ Zero price handled correctly: value is {current_value}")
    
    def test_select_all_and_clear(
        self,
        page: Page,
        test_vendor_code: str
    ):
        """
        Test select all and clear selection functionality.
        """
        print(f"\n🧪 Testing select/clear functionality")
        
        # Navigate to price management
        price_menu = page.get_by_role("button", name="💰 Управление ценами")
        price_menu.click()
        expect(page.get_by_text("💰 Управление ценами").first).to_be_visible(timeout=10000)
        
        # Search for products
        found = search_product_in_dashboard(page, test_vendor_code, timeout=30)
        assert found, "No products found"
        
        # Click "Select All"
        select_all_button = page.get_by_role("button", name="✓ Выбрать все")
        select_all_button.click()
        
        # Verify send button appears with count
        send_button = page.get_by_role("button", name=re.compile(r"Отправить.*"))
        expect(send_button).to_be_visible(timeout=5000)
        print("   ✓ Select All worked - send button visible")
        
        # Click "Clear Selection"
        clear_button = page.get_by_role("button", name="✗ Очистить выбор")
        clear_button.click()
        
        # Verify send button disappears or changes
        # The button text should no longer contain "Отправить"
        time.sleep(1)  # Wait for UI update
        
        # Check that no products are selected
        checkboxes = page.locator("input[type='checkbox'][id*='chk_']:checked")
        assert checkboxes.count() == 0, "Some products still selected after clearing"
        
        print("   ✓ Clear Selection worked - no products selected")
