@echo off
REM ============================================
REM  AFFICHAGE CLIENT - Lanceur Windows
REM  Double ecran pour caisse Flexo 6
REM ============================================
title Affichage Client - Serveur

cd /d "%~dp0\.."

echo.
echo  ==========================================
echo   AFFICHAGE CLIENT - Demarrage...
echo  ==========================================
echo.

REM Verifier que Python est installe
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERREUR] Python n'est pas installe ou pas dans le PATH.
    echo.
    echo Veuillez installer Python depuis https://www.python.org/downloads/
    echo Cochez "Add Python to PATH" lors de l'installation.
    echo.
    pause
    exit /b 1
)

REM Demarrer le serveur en arriere-plan
echo [1/3] Demarrage du serveur local...
start /B python server\server.py --port 5555

REM Attendre que le serveur demarre
timeout /t 2 /nobreak >nul

REM Demarrer le moniteur Flexo 6
echo [2/3] Demarrage du moniteur Flexo 6...
start /B python scripts\flexo_monitor.py

REM Ouvrir l'affichage client dans Chrome en mode kiosque sur le 2eme ecran
echo [3/3] Ouverture de l'affichage client...

REM Detecter Chrome
set CHROME_PATH=
if exist "C:\Program Files\Google\Chrome\Application\chrome.exe" (
    set "CHROME_PATH=C:\Program Files\Google\Chrome\Application\chrome.exe"
)
if exist "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe" (
    set "CHROME_PATH=C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
)

if defined CHROME_PATH (
    echo Ouverture avec Google Chrome en mode kiosque...
    REM --kiosk = plein ecran sans barre d'adresse
    REM --window-position pour positionner sur le 2eme ecran
    REM Ajustez les coordonnees selon votre config ecran
    start "" "%CHROME_PATH%" --kiosk --new-window --window-position=1920,0 --app=http://localhost:5555
) else (
    echo Chrome non detecte, ouverture avec le navigateur par defaut...
    start http://localhost:5555
)

echo.
echo  ==========================================
echo   AFFICHAGE CLIENT DEMARRE !
echo  ==========================================
echo.
echo   Serveur: http://localhost:5555
echo   Demo:    http://localhost:5555?demo=1
echo.
echo   Appuyez sur une touche pour arreter...
echo  ==========================================
pause >nul

REM Arreter les processus
taskkill /f /im python.exe /fi "WINDOWTITLE eq Affichage*" >nul 2>&1
echo Serveur arrete.
