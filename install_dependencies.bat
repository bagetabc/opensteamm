@echo off
chcp 65001 > nul
title Установка зависимостей OpenSteamM
color 0A

echo ========================================
echo    УСТАНОВКА ЗАВИСИМОСТЕЙ
echo ========================================
echo.

python --version > nul 2>&1
if errorlevel 1 (
    echo [ОШИБКА] Python не установлен!
    pause
    exit /b 1
)

echo [*] Установка requests...
pip install requests

echo.
echo [*] Установка pillow (для иконок)...
pip install pillow

echo.
echo ========================================
echo    ГОТОВО!
echo ========================================
pause