
import pytest
from playwright.sync_api import Page, expect

def test_home_navigation(logged_in_page: Page, navigate):
    page = logged_in_page
    navigate("Главная")
    expect(page.locator(".main-header")).to_contain_text("Сводка по финансам")

def test_home_metrics(logged_in_page: Page, navigate):
    page = logged_in_page
    navigate("Главная")
    expect(page.get_by_text("Выручка")).to_be_visible()
    expect(page.get_by_text("Продаж")).to_be_visible()
