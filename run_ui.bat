@echo off
chcp 65001 >nul
title 台北雙星研究引擎 (UI-0 預覽介面)

echo ========================================================
echo   台北雙星土地型自住房研究引擎 - 啟動 UI 介面
echo ========================================================
echo.
echo 正在啟動 Streamlit 互動預覽...
echo.

uv run streamlit run src/twintower/ui/app.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [錯誤] 啟動失敗，結束代碼: %ERRORLEVEL%
    pause
)
