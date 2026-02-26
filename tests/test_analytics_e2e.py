
import pytest
from playwright.sync_api import Page, expect

@pytest.fixture(scope="function", autouse=True)
def before_each(page: Page):
    # Заходим на страницу дашборда
    page.goto("http://localhost:8501")
    
    # Ждем загрузки сайдбара
    page.wait_for_selector("[data-testid='stSidebar']")

def test_analytics_page_navigation_and_ui(page: Page):
    # 1. Авторизация (вводим мок-токен чтобы открылось меню)
    token_input = page.get_by_label("Введите токен WB API:")
    if token_input.is_visible():
        token_input.fill("test_mock_token_12345")
        page.get_by_role("button", name="🚀 Подключиться").click()
    
    # Ждем появления кнопок навигации
    page.wait_for_selector("button:has-text('📊 Аналитика')")
    
    # 2. Переход в раздел Аналитика
    page.get_by_role("button", name="📊 Аналитика").click()
    
    # 3. Проверка заголовка страницы
    expect(page.locator(".main-header")).to_contain_text("Аналитика продаж")
    
    # 4. Проверка наличия вкладок
    expect(page.get_by_role("tab", name="📈 Общая аналитика")).to_be_visible()
    expect(page.get_by_role("tab", name="💰 Маржинальность")).to_be_visible()
    
    # 5. Проверка селекторов периода
    expect(page.get_by_text("Период:")).to_be_visible()
    
    # 6. Клик по кнопке "Обновить"
    page.get_by_role("button", name="🔄 Обновить").click()
    
    # Проверяем, что не выскочило системной ошибки отрисовки (красный блок Streamlit)
    # В Streamlit ошибки отрисовки обычно имеют класс .stException или текст "Traceback"
    expect(page.locator("body")).not_to_contain_text("Traceback")
    expect(page.locator("body")).not_to_contain_text("NoneType")

def test_margin_tab_functionality(page: Page):
    # 1. Авторизация (если нужно)
    if page.get_by_label("Введите токен WB API:").is_visible():
        page.get_by_label("Введите токен WB API:").fill("test_mock_token")
        page.get_by_role("button", name="🚀 Подключиться").click()
    
    page.get_by_role("button", name="📊 Аналитика").click()
    
    # Переходим на вкладку Маржинальность
    page.get_by_role("tab", name="💰 Маржинальность").click()
    
    # Проверяем наличие кнопок управления БД
    expect(page.get_by_role("button", name="📥 Загрузить новые отчеты")).to_be_visible()
    expect(page.get_by_role("button", name="📊 Рассчитать маржинальность")).to_be_visible()
    
    # Проверяем статистику БД (должна быть видна или "Нет данных")
    expect(page.get_by_text("Записей в базе")).to_be_visible()
