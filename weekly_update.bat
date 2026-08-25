:: Weekly run: pull the latest AP rankings and refresh the current-week graphs.
@echo off
echo ---------------
echo AP CFB XC weekly update
echo.

:: Determine the repo root (directory this script lives in)
set "REPO_DIR=%~dp0"

:: Locate the project's venv relative to the repo root - no hardcoded machine paths
set "VPYTHON_PATH=%REPO_DIR%venv\Scripts\python.exe"

if not exist "%VPYTHON_PATH%" (
    echo Error: no venv found at "%VPYTHON_PATH%"
    echo Create one with: python -m venv venv ^&^& venv\Scripts\pip install -r requirements.in
    exit /b 1
)

echo Using Python: "%VPYTHON_PATH%"
echo.

"%VPYTHON_PATH%" "%REPO_DIR%weekly_update.py"

echo ----------------
:: Uncomment the line below if you want the window to stay open on manual/double-click runs.
:: This should stay commented out for unattended schtasks runs.
:: pause
