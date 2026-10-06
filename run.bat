@echo off
chcp 65001 >nul
title LaunchReady - Website QA Auditor
echo ========================================================
echo   LaunchReady - בדיקת מוכנות אתר למסירה ללקוח
echo ========================================================
echo.
echo מפעיל את השרת בכתובת: http://127.0.0.1:8080
echo לחץ Ctrl+C כדי לעצור את השרת.
echo.
set PYTHONUTF8=1
python -m uvicorn main:app --host 127.0.0.1 --port 8080
pause
