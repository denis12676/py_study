import pytest
import time
from playwright.sync_api import Page, expect

@pytest.fixture(scope="function")
def logged_in_page(page: Page):
    page.set_viewport_size({"width": 1280, "height": 800})
    page.goto("http://localhost:8501", timeout=60000)
    
    # Ждем отрисовку хоть чего-то
    page.wait_for_selector("[data-testid='stSidebar']", timeout=20000)
    
    # Если видим поле ввода токена - вводим
    token_input = page.get_by_label("Введите токен WB API:")
    if token_input.is_visible():
        token_input.fill("test_mock_token")
        page.get_by_role("button", name="🚀 Подключиться").click()
        # Ждем исчезновения поля ввода или появления кнопки Отключиться
        page.wait_for_selector("button:has-text('🚪 Отключиться')", timeout=20000)
            
    return page

@pytest.fixture
def navigate(logged_in_page: Page):
    def _navigate(menu_name: str):
        # Находим кнопку в сайдбаре по тексту
        btn = logged_in_page.locator(f"button:has-text('{menu_name}')")
        btn.wait_for(state="visible", timeout=10000)
        btn.click()
        # Ждем завершения анимации Streamlit (пропадание спиннера или изменение URL не работает, поэтому спим немного)
        time.sleep(1.5)
    return _navigate
