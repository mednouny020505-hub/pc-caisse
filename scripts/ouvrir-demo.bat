@echo off
REM ============================================
REM  Ouvre l'affichage client en mode DEMO
REM  (sans Flexo 6, pour tester)
REM ============================================
title Affichage Client - Demo

cd /d "%~dp0\.."

echo Demarrage du serveur...
start /B python server\server.py --port 5555

timeout /t 2 /nobreak >nul

echo Ouverture du mode demo dans le navigateur...
start http://localhost:5555?demo=1

echo.
echo Mode demo demarre ! Appuyez sur une touche pour arreter...
pause >nul
taskkill /f /im python.exe >nul 2>&1
