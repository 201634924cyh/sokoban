@echo off
REM Sokoban launcher (ASCII only - keep this file free of non-ASCII text)
setlocal

cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 goto nopython

python -c "import pygame" >nul 2>nul
if errorlevel 1 goto nopygame

python sokoban.py
goto end

:nopython
echo.
echo [ERROR] Python not found in PATH.
echo         Install Python 3.9+ from https://www.python.org/downloads/
echo         Remember to tick "Add Python to PATH" during installation.
echo.
pause
goto end

:nopygame
echo.
echo [ERROR] pygame is not installed.
echo         Run this command first:
echo.
echo             python -m pip install -i https://mirrors.cloud.tencent.com/pypi/simple pygame
echo.
echo         Or double-click install_deps.bat in this folder.
echo.
pause
goto end

:end
endlocal
