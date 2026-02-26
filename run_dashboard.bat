@echo off
chcp 65001 >nul
echo ==========================================
echo  Wildberries AI Dashboard
echo ==========================================
echo.

if not exist .venv\Scripts\python.exe (
    echo Creating virtual environment...
    py -m venv .venv
    if errorlevel 1 (
        echo Failed to create virtual environment.
        pause
        exit /b 1
    )
)

echo Installing dependencies...
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 (
    echo Failed to install dependencies.
    pause
    exit /b 1
)

echo Starting dashboard...
echo.
echo After starting, open browser at: http://127.0.0.1:8501
echo.
.\.venv\Scripts\python.exe -m streamlit run dashboard.py --server.address 127.0.0.1 --server.port 8501

pause
