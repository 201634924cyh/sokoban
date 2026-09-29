@echo off
REM Install pygame from a China-friendly mirror (ASCII only)
setlocal
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Python not found in PATH. Install Python 3.9+ first.
  pause
  goto end
)

echo Installing pygame from Tencent Cloud mirror...
python -m pip install -i https://mirrors.cloud.tencent.com/pypi/simple pygame
if errorlevel 1 (
  echo.
  echo Tencent mirror failed, trying Huawei mirror...
  python -m pip install -i https://repo.huaweicloud.com/repository/pypi/simple pygame
)

echo.
echo Done. Now double-click run.bat to play.
pause

:end
endlocal
