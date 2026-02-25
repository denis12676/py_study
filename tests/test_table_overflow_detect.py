"""
Playwright test to DETECT and PROVE table overflow issue exists.

This test intentionally checks for overflow - if overflow is detected,
the test FAILS, proving the problem exists.

Usage: python -m pytest tests/test_table_overflow_detect.py -v
"""

import pytest
from playwright.sync_api import sync_playwright, Page
import subprocess
import time
import signal
import sys
import os


@pytest.fixture(scope="module")
def dashboard_server():
    """Start Streamlit dashboard server."""
    process = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", "dashboard.py", 
         "--server.port", "8501", "--server.headless", "true"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )
    
    time.sleep(10)
    yield "http://localhost:8501"
    
    process.send_signal(signal.SIGTERM)
    process.wait(timeout=5)


@pytest.fixture
def browser_page():
    """Create browser page with standard viewport."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        yield page
        browser.close()


class TestTableOverflowDetection:
    """Test suite that DETECTS table overflow problem."""
    
    def test_detect_horizontal_overflow(self, browser_page: Page, dashboard_server: str):
        """Test that DETECTS if page has horizontal overflow after loading FBO stocks."""
        page = browser_page
        page.goto(dashboard_server)
        page.wait_for_selector("[data-testid='stAppViewContainer']", timeout=15000)
        
        # Navigate to inventory section
        nav_items = page.locator(".stRadio label")
        for i in range(nav_items.count()):
            text = nav_items.nth(i).text_content()
            if text and ("склад" in text.lower() or "остатки" in text.lower()):
                nav_items.nth(i).click()
                time.sleep(2)
                break
        
        # Click load button for FBO stocks
        load_buttons = page.locator("button:has-text('Загрузить')")
        for i in range(load_buttons.count()):
            btn = load_buttons.nth(i)
            if btn.count() > 0 and "fbo" in btn.text_content().lower():
                btn.click()
                time.sleep(15)
                break
        
        # Measure overflow
        dimensions = page.evaluate("""
            () => ({
                viewportWidth: window.innerWidth,
                scrollWidth: document.documentElement.scrollWidth,
                hasHorizontalScroll: document.documentElement.scrollWidth > document.documentElement.clientWidth
            })
        """)
        
        print(f"\n📊 Viewport: {dimensions['viewportWidth']}px, Scroll: {dimensions['scrollWidth']}px")
        print(f"   Has overflow: {dimensions['hasHorizontalScroll']}")
        
        # Save evidence
        os.makedirs("tests/screenshots", exist_ok=True)
        screenshot = f"tests/screenshots/overflow_{int(time.time())}.png"
        page.screenshot(path=screenshot, full_page=True)
        
        # FAIL if overflow detected - proves problem exists
        assert not dimensions['hasHorizontalScroll'], (
            f"❌ OVERFLOW DETECTED! Scroll width ({dimensions['scrollWidth']}px) > Viewport ({dimensions['viewportWidth']}px). "
            f"Evidence: {screenshot}"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
