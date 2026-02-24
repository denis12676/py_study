@echo off
chcp 65001 >nul
echo ==========================================
echo  QUICK DEPLOY TO STREAMLIT CLOUD
echo ==========================================
echo.
echo This script will help deploy safely.
echo.

REM Check if we're in git repo
if not exist .git (
    echo ERROR: Not a git repository!
    echo Run: git init
    pause
    exit /b 1
)

echo Step 1: Checking security...
python check_security.py
if errorlevel 1 (
    echo.
    echo SECURITY CHECK FAILED!
    echo Fix issues before deploying.
    pause
    exit /b 1
)

echo.
echo Step 2: Creating .env backup...
if exist .env (
    copy .env .env.backup
    echo [OK] Backup created: .env.backup
)

echo.
echo Step 3: Removing sensitive files from git...
git rm --cached .env 2>nul
git rm --cached .streamlit/secrets.toml 2>nul
echo [OK] Removed from git index

echo.
echo Step 4: Committing code...
git add -A
git commit -m "Prepare for Streamlit Cloud deploy"
echo [OK] Code committed

echo.
echo ==========================================
echo  NEXT STEPS (Manual):
echo ==========================================
echo.
echo 1. Push to GitHub:
echo    git push origin main
echo.
echo 2. Go to https://streamlit.io/cloud
echo.
echo 3. Click "New app" and select your repo
echo.
echo 4. In Settings ^> Secrets, add:
echo    WB_API_TOKEN = your_real_token_here
echo.
echo 5. Click Deploy!
echo.
echo ==========================================
echo.

pause
