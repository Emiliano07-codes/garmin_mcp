@echo off
chcp 65001 >nul
echo ============================================================
echo   Garmin Performance Lab V4.2 - Generacion de Panel
echo   Coherencia Cromatica, Predicciones, Consistencia y Tunel
echo ============================================================
echo.
cd /d "%~dp0"

echo [1/2] Ejecutando extractor y generador V4.2...
uv run python dashboard_v4_2.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Hubo un problema al generar el panel V4.2.
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo [2/2] Abriendo panel interactivo V4.2 en el navegador...
start "" "index_v4_2.html"

echo.
echo ✓ Panel V4.2 listo y abierto con exito.
pause
