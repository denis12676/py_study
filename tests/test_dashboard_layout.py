"""Playwright tests for dashboard table overflow issue."""

import pytest
from playwright.sync_api import Page, expect, sync_playwright
import subprocess
import time
import signal
import sys
import os


@pytest.fixture(scope="module")
def dashboard_server():
    """Start the Streamlit dashboard server for testing."""
    process = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", "dashboard.py", "--server.port", "8502"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )
    
    time.sleep(8)
    yield "http://localhost:8502"
    
    process.send_signal(signal.SIGTERM)
    process.wait(timeout=5)


@pytest.fixture
def page():
    """Create a browser page for testing."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        yield page
        browser.close()


class TestTableOverflow:
    """Test suite for table overflow/layout issues."""
    
    def test_page_width_within_viewport(self, page: Page, dashboard_server: str):
        """Test that page width doesn't exceed viewport after loading data."""
        page.goto(dashboard_server)
        page.wait_for_load_state("networkidle")
        
        viewport_width = page.viewport_size["width"]
        body_width = page.evaluate("document.body.scrollWidth")
        
        assert body_width <= viewport_width + 20, (
            f"Page width ({body_width}px) exceeds viewport ({viewport_width}px). "
            f"Horizontal overflow detected!"
        )
    
    def test_no_horizontal_scrollbar(self, page: Page, dashboard_server: str):
        """Test that no horizontal scrollbar appears on page."""
        page.goto(dashboard_server)
        page.wait_for_load_state("networkidle")
        
        has_horizontal_scroll = page.evaluate(
            "document.documentElement.scrollWidth > document.documentElement.clientWidth"
        )
        
        assert not has_horizontal_scroll, (
            "Horizontal scrollbar detected - page content is overflowing!"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
