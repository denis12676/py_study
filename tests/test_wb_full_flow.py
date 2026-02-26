
import pytest
import time
from playwright.sync_api import Page, expect

def test_wb_dashboard_full_flow(logged_in_page: Page, navigate):
    page = logged_in_page
    
    # 1. Главная
    navigate("Главная")
    expect(page.locator(".main-header")).to_contain_text("Сводка по финансам")
    print("✅ Главная: OK")
    
    # 2. Аналитика
    navigate("Аналитика")
    expect(page.locator(".main-header")).to_contain_text("Аналитика продаж")
    expect(page.get_by_role("tab", name="📈 Общая аналитика")).to_be_visible()
    print("✅ Аналитика: OK")
    
    # 3. Товары
    navigate("Товары")
    expect(page.locator(".main-header")).to_contain_text("Управление товарами")
    print("✅ Товары: OK")
    
    # 4. Остатки
    navigate("Остатки")
    expect(page.locator(".main-header")).to_contain_text("Остатки товаров")
    print("✅ Остатки: OK")
    
    # 5. Реклама
    navigate("Реклама")
    expect(page.locator(".main-header")).to_contain_text("Управление рекламой")
    print("✅ Реклама: OK")
    
    # 6. AI Чат
    navigate("AI Чат")
    expect(page.locator(".main-header")).to_contain_text("AI Ассистент")
    # Проверяем поле ввода с запасом по времени
    page.wait_for_selector("input[aria-label='Ваш запрос:']", timeout=10000)
    print("✅ AI Чат: OK")
    
    # 7. Автоцены
    navigate("Автоцены")
    expect(page.locator(".main-header")).to_contain_text("Автоматическое ценообразование")
    print("✅ Автоцены: OK")

def test_logout(logged_in_page: Page):
    page = logged_in_page
    page.get_by_role("button", name="🚪 Отключиться").click()
    expect(page.get_by_label("Введите токен WB API:")).to_be_visible()
    print("✅ Выход: OK")
