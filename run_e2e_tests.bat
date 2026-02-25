@echo off
chcp 65001 >nul
echo ==========================================
echo  Wildberries E2E Tests (Playwright)
echo ==========================================
echo.

REM Check if pytest-playwright is installed
python -c "import pytest_playwright" 2>nul
if errorlevel 1 (
    echo Installing Playwright dependencies...
    pip install pytest-playwright
    playwright install chromium
)

echo Starting E2E tests...
echo.
echo Make sure dashboard is running: streamlit run dashboard.py
echo Or the test will start it automatically
echo.

REM Run tests with verbose output and headed mode (visible browser)
pytest tests/e2e/ -v --headed --slowmo 500 %*

echo.
echo ==========================================
echo  Tests completed
echo ==========================================

pause