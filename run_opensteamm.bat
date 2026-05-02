@echo off
chcp 65001 > nul
title OpenSteamM
color 0A
cd /d "%~dp0"

echo ========================================
echo         OPENSTEAMM
echo ========================================
echo.

python --version > nul 2>&1
if errorlevel 1 (
    echo [ОШИБКА] Python не установлен!
    pause
    exit /b 1
)

if not exist "opensteamm_gui.py" (
    echo [ОШИБКА] opensteamm_gui.py не найден!
    pause
    exit /b 1
)

pip install requests > nul 2>&1

echo [*] Запуск...
python opensteamm_gui.py

pause