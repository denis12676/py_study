@echo off
chcp 65001 >nul
REM Test runner script for Windows

echo ==========================================
echo  Wildberries AI Agent - Test Runner
echo ==========================================
echo.

IF "%1"=="" (
    echo Usage: run_tests.bat [command]
    echo.
    echo Commands:
    echo   all          - Run all tests
    echo   unit         - Run unit tests only
    echo   coverage     - Run tests with coverage
    echo   wb_client    - Test API client
    echo   managers     - Test business logic
    echo   ai_agent     - Test AI agent
    echo   dashboard    - Test dashboard
    echo   help         - Show help
    echo.
    exit /b 1
)

IF "%1"=="all" (
    echo Running all tests...
    pytest tests/ -v
    exit /b %ERRORLEVEL%
)

IF "%1"=="unit" (
    echo Running unit tests...
    pytest tests/ -m unit -v
    exit /b %ERRORLEVEL%
)

IF "%1"=="coverage" (
    echo Running tests with coverage...
    pytest tests/ --cov=. --cov-report=html --cov-report=term
    echo.
    echo Coverage report saved to: htmlcov/index.html
    exit /b %ERRORLEVEL%
)

IF "%1"=="wb_client" (
    echo Testing API client...
    pytest tests/test_wb_client.py -v
    exit /b %ERRORLEVEL%
)

IF "%1"=="managers" (
    echo Testing business logic...
    pytest tests/test_managers.py -v
    exit /b %ERRORLEVEL%
)

IF "%1"=="ai_agent" (
    echo Testing AI agent...
    pytest tests/test_ai_agent.py -v
    exit /b %ERRORLEVEL%
)

IF "%1"=="dashboard" (
    echo Testing dashboard...
    pytest tests/test_dashboard.py -v
    exit /b %ERRORLEVEL%
)

IF "%1"=="help" (
    echo Wildberries AI Agent Test Runner
echo ==========================================
echo.
echo Available commands:
echo.
echo   all          - Run all tests
echo   unit         - Run unit tests only (fast)
echo   coverage     - Run tests with code coverage
echo   wb_client    - Test API client
echo   managers     - Test business logic
echo   ai_agent     - Test AI agent
echo   dashboard    - Test dashboard
echo   help         - Show this help
echo.
echo Examples:
echo   run_tests.bat all
echo   run_tests.bat unit
echo   run_tests.bat coverage
echo.
)
