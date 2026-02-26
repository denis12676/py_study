
import pytest
from playwright.sync_api import Page, expect

def test_autoprices_page(logged_in_page: Page, navigate):
    page = logged_in_page
    navigate("Автоцены")
    expect(page.locator(".main-header")).to_contain_text("Автоматическое ценообразование")
    expect(page.get_by_role("tab", name="⚙️ Стратегии")).to_be_visible()
