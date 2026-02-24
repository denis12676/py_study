@echo off
chcp 65001 >nul
echo ==========================================
echo  PUSH TO GITHUB
echo ==========================================
echo.
echo This script will guide you to push to GitHub.
echo.

REM Check git status
cd wildberries-ai-agent
git status >nul 2>&1
if errorlevel 1 (
    echo ERROR: Git not initialized!
    pause
    exit /b 1
)

echo Step 1: Check what we have...
git log --oneline -1
echo.

echo Step 2: You need to create a GitHub repository first!
echo.
echo Instructions:
echo 1. Go to https://github.com/new
echo 2. Enter repository name: wb-ai-agent
echo 3. Choose Public or Private
echo 4. DO NOT initialize with README (we have one already)
echo 5. Click "Create repository"
echo.
echo After creating, copy the repository URL and paste it here:
set /p REPO_URL="GitHub repository URL: "

echo.
echo Step 3: Adding remote repository...
git remote add origin %REPO_URL%
echo [OK] Remote added

echo.
echo Step 4: Pushing to GitHub...
git push -u origin master
echo [OK] Code pushed!

echo.
echo ==========================================
echo  SUCCESS!
echo ==========================================
echo.
echo Your code is now on GitHub!
echo.
echo Next step: Deploy to Streamlit Cloud
echo 1. Go to https://streamlit.io/cloud
echo 2. Click "New app"
echo 3. Select your GitHub repository
echo 4. Add WB_API_TOKEN in Settings ^> Secrets
echo 5. Deploy!
echo.

pause
