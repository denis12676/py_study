"""
Pytest fixtures for E2E tests with Playwright and Streamlit dashboard.
"""

import os
import sys
import time
import subprocess
import signal
from pathlib import Path
from typing import Generator, Optional
import pytest
from playwright.sync_api import sync_playwright, Page, Browser, BrowserContext, expect

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from .helpers import wait_for_streamlit_app, take_screenshot_on_failure, get_api_token_from_env


@pytest.fixture(scope="session")
def browser() -> Generator[Browser, None, None]:
    """
    Launch Playwright browser for the test session.
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # Set to True for CI
        yield browser
        browser.close()


@pytest.fixture(scope="session")
def dashboard_server(tmp_path_factory) -> Generator[str, None, None]:
    """
    Start Streamlit dashboard server in background.
    
    Yields:
        str: URL of the running dashboard (http://localhost:8501)
    """
    dashboard_url = "http://localhost:8501"
    dashboard_file = project_root / "dashboard.py"
    
    if not dashboard_file.exists():
        raise FileNotFoundError(f"Dashboard file not found: {dashboard_file}")
    
    # Check if API token is available
    api_token = get_api_token_from_env()
    if not api_token:
        pytest.skip("WB_API_TOKEN not found in .env file or environment variables")
    
    # Create a temporary .env file with the token for the subprocess
    env = os.environ.copy()
    env['WB_API_TOKEN'] = api_token
    env['STREAMLIT_SERVER_HEADLESS'] = 'true'
    env['STREAMLIT_BROWSER_GATHER_USAGE_STATS'] = 'false'
    
    # Start Streamlit server
    cmd = [
        sys.executable, "-m", "streamlit", "run",
        str(dashboard_file),
        "--server.port", "8501",
        "--server.headless", "true",
        "--browser.gatherUsageStats", "false",
        "--server.address", "localhost",
        "--server.maxUploadSize", "50"
    ]
    
    print(f"\n🚀 Starting Streamlit server...")
    print(f"   Command: {' '.join(cmd)}")
    
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=str(project_root),
        env=env,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0
    )
    
    # Wait for server to start
    max_wait = 60
    start_time = time.time()
    server_ready = False
    
    print(f"⏳ Waiting for server to start (max {max_wait}s)...")
    
    while time.time() - start_time < max_wait:
        try:
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(('localhost', 8501))
            sock.close()
            
            if result == 0:
                server_ready = True
                print(f"✅ Streamlit server is ready at {dashboard_url}")
                break
        except Exception:
            pass
        
        # Check if process is still running
        if process.poll() is not None:
            stdout, stderr = process.communicate()
            print(f"❌ Server process exited prematurely!")
            print(f"   STDOUT: {stdout.decode()[-500:] if stdout else 'None'}")
            print(f"   STDERR: {stderr.decode()[-500:] if stderr else 'None'}")
            raise RuntimeError("Streamlit server failed to start")
        
        time.sleep(0.5)
    
    if not server_ready:
        process.terminate()
        try:
            stdout, stderr = process.communicate(timeout=5)
        except:
            pass
        raise RuntimeError(f"Streamlit server did not start within {max_wait} seconds")
    
    # Give the server a moment to fully initialize
    time.sleep(2)
    
    yield dashboard_url
    
    # Cleanup: terminate the server
    print(f"\n🛑 Stopping Streamlit server...")
    
    if os.name == 'nt':
        # Windows: send CTRL_BREAK_EVENT to the process group
        try:
            os.kill(process.pid, signal.CTRL_BREAK_EVENT)
        except:
            pass
    else:
        # Unix: terminate gracefully
        process.terminate()
    
    # Wait for process to finish
    try:
        process.wait(timeout=5)
    except:
        # Force kill if necessary
        process.kill()
        process.wait()
    
    print("✅ Server stopped")


@pytest.fixture
def browser_context(
    browser: Browser,
    tmp_path,
    request
) -> Generator[BrowserContext, None, None]:
    """
    Create browser context with saved auth state.
    
    The context is configured to:
    - Accept downloads
    - Set viewport size
    - Handle dialogs automatically
    """
    # Create a temporary directory for auth state
    auth_dir = tmp_path / "auth"
    auth_dir.mkdir(exist_ok=True)
    auth_file = auth_dir / "auth_state.json"
    
    # Create context with settings
    context = browser.new_context(
        viewport={"width": 1920, "height": 1080},
        accept_downloads=True,
        bypass_csp=True,
        locale="ru-RU",
        timezone_id="Europe/Moscow"
    )
    
    # Set up screenshot on failure
    test_name = request.node.name
    
    yield context
    
    # Cleanup
    context.close()


@pytest.fixture
def page(browser_context: BrowserContext, dashboard_server: str) -> Generator[Page, None, None]:
    """
    Create a new page in the browser context and navigate to dashboard.
    
    The page will be pre-authenticated if auth state exists.
    """
    page = browser_context.new_page()
    
    # Set default timeout for expect
    expect.set_options(timeout=30000)
    
    # Navigate to dashboard
    print(f"\n🌐 Navigating to dashboard: {dashboard_server}")
    page.goto(dashboard_server, wait_until="networkidle")
    
    # Wait for app to load
    wait_for_streamlit_app(page, timeout=30)
    
    yield page
    
    # Cleanup
    page.close()


@pytest.fixture(autouse=True)
def screenshot_on_failure(request, page: Page):
    """
    Automatically take screenshot when test fails.
    
    This fixture runs automatically for all tests.
    """
    yield
    
    # Check if test failed
    if request.node.rep_call.failed if hasattr(request.node, 'rep_call') else False:
        test_name = request.node.name
        screenshot_path = take_screenshot_on_failure(page, test_name)
        print(f"\n📸 Screenshot saved: {screenshot_path}")


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """
    Hook to capture test result status for screenshot_on_failure fixture.
    """
    outcome = yield
    rep = outcome.get_result()
    
    # Store result on the item for access in fixtures
    if call.when == "call":
        item.rep_call = rep


@pytest.fixture(scope="session")
def api_token() -> str:
    """
    Get API token from environment or .env file.
    
    Raises:
        pytest.skip: If token is not available
    """
    token = get_api_token_from_env()
    if not token:
        pytest.skip("WB_API_TOKEN not found. Please set it in .env file or environment variable.")
    return token


@pytest.fixture
def test_vendor_code() -> str:
    """Vendor code of the test product."""
    return "LM-10160"


@pytest.fixture
def original_price(request, api_token: str, test_vendor_code: str) -> Generator[int, None, None]:
    """
    Fixture to backup original price before test and restore after.
    
    Yields:
        int: Original price of the test product
    """
    from .helpers import get_product_price_api, update_price_api
    
    # Get original price
    try:
        original = get_product_price_api(test_vendor_code, api_token)
        print(f"\n💾 Original price for {test_vendor_code}: {original} RUB")
    except Exception as e:
        pytest.skip(f"Could not get original price: {e}")
        return
    
    yield original
    
    # Restore original price after test (even if test failed)
    print(f"\n🔄 Restoring original price: {original} RUB")
    try:
        update_price_api(test_vendor_code, original, discount=0, api_token=api_token)
        print(f"✅ Price restored to {original} RUB")
    except Exception as e:
        print(f"⚠️ Failed to restore original price: {e}")
