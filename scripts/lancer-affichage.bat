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

REM Installer les dependances si necessaire
echo [0/4] Verification des dependances...
pip install pynput >nul 2>&1
pip install firebirdsql >nul 2>&1

REM Demarrer le serveur en arriere-plan
echo [1/4] Demarrage du serveur local (port 5555)...
start /B "AffichageServeur" python server\server.py --port 5555

REM Attendre que le serveur demarre
timeout /t 2 /nobreak >nul

REM Demarrer le moniteur Flexo 6 (capture scanner + base)
echo [2/4] Demarrage du moniteur temps reel Flexo 6...
start /B "AffichageMoniteur" python scripts\flexo_monitor.py

REM Attendre le moniteur
timeout /t 1 /nobreak >nul

REM Ouvrir l'affichage client dans Chrome en mode kiosque sur le 2eme ecran
echo [3/4] Ouverture de l'affichage client sur le 2eme ecran...

REM Detecter Chrome
set CHROME_PATH=
if exist "C:\Program Files\Google\Chrome\Application\chrome.exe" (
    set "CHROME_PATH=C:\Program Files\Google\Chrome\Application\chrome.exe"
)
if exist "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe" (
    set "CHROME_PATH=C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
)

REM Detecter Edge (alternative)
set EDGE_PATH=
if exist "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" (
    set "EDGE_PATH=C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
)

if defined CHROME_PATH (
    echo Ouverture avec Google Chrome en mode kiosque...
    REM --kiosk = plein ecran sans barre d'adresse
    REM --window-position pour positionner sur le 2eme ecran
    REM IMPORTANT: Ajustez 1920,0 selon votre resolution d'ecran principal
    start "" "%CHROME_PATH%" --kiosk --new-window --window-position=1920,0 --app=http://localhost:5555
) else if defined EDGE_PATH (
    echo Ouverture avec Microsoft Edge en mode kiosque...
    start "" "%EDGE_PATH%" --kiosk --new-window --window-position=1920,0 --app=http://localhost:5555
) else (
    echo Navigateur non detecte, ouverture par defaut...
    start http://localhost:5555
)

echo [4/4] Pret !
echo.
echo  ==========================================
echo   AFFICHAGE CLIENT DEMARRE !
echo  ==========================================
echo.
echo   Serveur:    http://localhost:5555
echo   Demo:       http://localhost:5555?demo=1
echo.
echo   Le moniteur capture les scans en temps reel.
echo   Les produits s'affichent au moment du scan,
echo   AVANT la creation du ticket.
echo.
echo   Appuyez sur une touche pour tout arreter...
echo  ==========================================
pause >nul

REM Arreter proprement
echo Arret en cours...
taskkill /f /fi "WINDOWTITLE eq AffichageServeur" >nul 2>&1
taskkill /f /fi "WINDOWTITLE eq AffichageMoniteur" >nul 2>&1
echo Termine.
