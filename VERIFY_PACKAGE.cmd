@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"

where uv >nul 2>nul
if errorlevel 1 (
  echo uv가 필요합니다. INSTALL_WINDOWS_KO.md를 확인하세요.
  pause
  exit /b 1
)

uv sync --dev
if errorlevel 1 exit /b 1
uv run pytest
if errorlevel 1 exit /b 1
uv run python scripts\verify_release.py
if errorlevel 1 exit /b 1

echo.
echo 모든 공개 패키지 검사가 통과했습니다.
pause
endlocal
