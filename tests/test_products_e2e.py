
import pytest
from playwright.sync_api import Page, expect

def test_products_catalog_loading(logged_in_page: Page, navigate):
    page = logged_in_page
    navigate("Товары")
    
    expect(page.locator(".main-header")).to_contain_text("Управление товарами")
    page.get_by_role("tab", name="Каталог").click()
    page.get_by_role("button", name="🔄 Загрузить каталог").click()
    expect(page.locator("body")).not_to_contain_text("Traceback")

def test_products_search_tab(logged_in_page: Page, navigate):
    page = logged_in_page
    navigate("Товары")
    page.get_by_role("tab", name="Поиск").click()
    expect(page.get_by_placeholder("Введите артикул или название")).to_be_visible()
