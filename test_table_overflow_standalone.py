#!/usr/bin/env python
"""Standalone test for table overflow - run without pytest."""

from playwright.sync_api import sync_playwright
import subprocess
import time
import signal
import sys
import os


def test_table_overflow():
    """Test that verifies table overflow issue is fixed."""
    print("🚀 Starting Streamlit dashboard...")
    
    # Start dashboard
    process = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", "dashboard.py", "--server.port", "8503"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=os.path.dirname(os.path.abspath(__file__))
    )
    
    try:
        print("⏳ Waiting for server to start (8 seconds)...")
        time.sleep(8)
        
        print("🌐 Opening browser and testing...")
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1280, "height": 800})
            
            # Load page
            page.goto("http://localhost:8503")
            page.wait_for_load_state("networkidle")
            
            # Test 1: Check page width
            viewport_width = page.viewport_size["width"]
            body_width = page.evaluate("document.body.scrollWidth")
            
            print(f"\n📊 Test Results:")
            print(f"   Viewport width: {viewport_width}px")
            print(f"   Page width: {body_width}px")
            
            if body_width <= viewport_width + 20:
                print("   ✅ PASS: Page width is within viewport bounds")
            else:
                print(f"   ❌ FAIL: Page overflows by {body_width - viewport_width}px!")
                return False
            
            # Test 2: Check for horizontal scrollbar
            has_scroll = page.evaluate(
                "document.documentElement.scrollWidth > document.documentElement.clientWidth"
            )
            
            if not has_scroll:
                print("   ✅ PASS: No horizontal scrollbar detected")
            else:
                print("   ❌ FAIL: Horizontal scrollbar present!")
                return False
            
            # Test 3: Screenshot
            print("\n📸 Taking screenshot...")
            page.screenshot(path="tests/screenshots/dashboard_test.png", full_page=True)
            print("   Screenshot saved to tests/screenshots/dashboard_test.png")
            
            browser.close()
            
        print("\n✅ All tests PASSED - table overflow issue is FIXED!")
        return True
        
    finally:
        print("\n🛑 Stopping dashboard server...")
        process.send_signal(signal.SIGTERM)
        process.wait(timeout=5)


if __name__ == "__main__":
    success = test_table_overflow()
    sys.exit(0 if success else 1)
