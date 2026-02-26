
import pytest
from playwright.sync_api import Page, expect

def test_inventory_page(logged_in_page: Page, navigate):
    page = logged_in_page
    navigate("Остатки")
    expect(page.locator(".main-header")).to_contain_text("Остатки товаров")
    expect(page.get_by_role("tab", name="FBS (склад продавца)")).to_be_visible()

def test_advertising_page(logged_in_page: Page, navigate):
    page = logged_in_page
    navigate("Реклама")
    expect(page.locator(".main-header")).to_contain_text("Управление рекламой")
    expect(page.get_by_role("button", name="🔄 Загрузить кампании")).to_be_visible()

def test_chat_page(logged_in_page: Page, navigate):
    page = logged_in_page
    navigate("AI Чат")
    expect(page.locator(".main-header")).to_contain_text("AI Ассистент")
    # Добавляем ожидание появления поля ввода
    input_field = page.get_by_placeholder("Ваш запрос:")
    input_field.wait_for(state="visible", timeout=10000)
    expect(input_field).to_be_visible()
