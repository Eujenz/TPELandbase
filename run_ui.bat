@echo off
cd /d "%~dp0"
title TwinTower Research Engine (UI-0)

echo ========================================================
echo   TwinTower Research Engine - Starting UI Preview
echo ========================================================
echo.

where uv >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    uv run streamlit run src/twintower/ui/app.py
) else (
    if exist ".venv\Scripts\streamlit.exe" (
        .venv\Scripts\streamlit.exe run src/twintower/ui/app.py
    ) else (
        echo [ERROR] Neither 'uv' nor '.venv\Scripts\streamlit.exe' was found.
        pause
    )
)

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Streamlit exited with error code: %ERRORLEVEL%
    pause
)
