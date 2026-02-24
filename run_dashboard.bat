@echo off
chcp 65001 >nul
echo ==========================================
echo  Wildberries AI Dashboard
echo ==========================================
echo.

REM Check if streamlit is installed
python -c "import streamlit" 2>nul
if errorlevel 1 (
    echo Installing dependencies...
    pip install -r requirements.txt
)

echo Starting dashboard...
echo.
echo After starting, open browser at: http://localhost:8501
echo.
streamlit run dashboard.py

pause
