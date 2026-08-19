@echo off
rem ============================================
rem  Character Card Maker - One-Click Launcher
rem  (Double-click to start, no console window)
rem ============================================
cd /d "%~dp0"

set "PYW1=C:\Users\Administrator\AppData\Local\Programs\Python\Python312\pythonw.exe"
set "PYW2=C:\Python312\pythonw.exe"
set "PYW3=C:\Python313\pythonw.exe"

set "FOUND="
if exist "%PYW1%" set "FOUND=%PYW1%"
if not defined FOUND if exist "%PYW2%" set "FOUND=%PYW2%"
if not defined FOUND if exist "%PYW3%" set "FOUND=%PYW3%"

if not defined FOUND (
    where pythonw >nul 2>nul && set "FOUND=pythonw"
)
if not defined FOUND (
    where python >nul 2>nul && set "FOUND=python"
)

if defined FOUND (
    start "" "%FOUND%" main.py
    exit /b 0
)

echo [ERROR] Python not found. Please install Python 3.10+.
pause