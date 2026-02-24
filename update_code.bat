@echo off
chcp 65001 >nul
echo ==========================================
echo  UPDATE CODE (Push new changes to GitHub)
echo ==========================================
echo.

cd wildberries-ai-agent

echo Step 1: Checking for changes...
git status --short
echo.

set /p CONFIRM="Proceed with update? (y/n): "
if /i not "%CONFIRM%"=="y" (
    echo Cancelled.
    pause
    exit /b 1
)

echo.
echo Step 2: Adding all changes...
git add -A
echo [OK] Changes added

echo.
set /p MESSAGE="Enter update description (or press Enter for default): "
if "%MESSAGE%"=="" (
    set MESSAGE=Code update
)

echo.
echo Step 3: Committing...
git commit -m "%MESSAGE%"
echo [OK] Committed

echo.
echo Step 4: Pushing to GitHub...
git push origin master
echo [OK] Pushed!

echo.
echo ==========================================
echo  SUCCESS! Code updated on GitHub
echo ==========================================
echo.
echo Streamlit Cloud will automatically reload
echo your app within 1-2 minutes.
echo.
echo To see changes immediately:
echo 1. Go to your app dashboard
echo 2. Click 'Manage app' 
echo 3. Click 'Reboot'
echo.

pause
