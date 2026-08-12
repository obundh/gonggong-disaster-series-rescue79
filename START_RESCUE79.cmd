@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"

echo.
echo ============================================================
echo   Rescue79 정적 7·9 모델 검토기
echo ============================================================
echo   연구·교육·시험용입니다.
echo   자동으로 112·119에 신고하거나 출동시키지 않습니다.
echo.

where uv >nul 2>nul
if errorlevel 1 (
  echo [준비 필요] uv 프로그램을 찾지 못했습니다.
  echo.
  echo 1. 인터넷 브라우저에서 https://docs.astral.sh/uv/ 를 엽니다.
  echo 2. Windows 설치 안내에 따라 uv를 한 번 설치합니다.
  echo 3. 이 파일을 다시 더블클릭합니다.
  echo.
  echo 보호자·교사·전산 담당자에게 INSTALL_WINDOWS_KO.md를 보여 주세요.
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo [처음 한 번만] 필요한 프로그램을 준비합니다.
  echo 인터넷과 컴퓨터 속도에 따라 오래 걸릴 수 있습니다.
  echo 이 창을 닫지 말고 기다려 주세요.
  echo.
  uv sync --no-dev
  if errorlevel 1 (
    echo.
    echo 설치에 실패했습니다. 위 오류를 사진으로 찍어 담당자에게 보여 주세요.
    pause
    exit /b 1
  )
)

echo 브라우저 화면을 엽니다. 이 검은 창은 닫지 마세요.
echo 완전히 종료하려면 이 창에서 Ctrl+C를 누르세요.
echo.
uv run --no-sync rescue79-reviewer

if errorlevel 1 (
  echo.
  echo 프로그램이 정상 종료되지 않았습니다. 위 오류를 확인해 주세요.
  pause
)
endlocal
