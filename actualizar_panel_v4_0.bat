@echo off
chcp 65001 > nul
echo ===================================================
echo   Garmin Performance Lab - Actualizando a V4.0
echo       (Google Cloud & Gemini Design System)
echo ===================================================
echo Sincronizando metricas Garmin, paleta pastel, bordes redondeados y layout blindado...
call uv run python dashboard_v4_0.py
if %ERRORLEVEL% NEQ 0 (
    echo Error al actualizar el panel V4.0. Revisa tu conexion o sesion.
    pause
    exit /b %ERRORLEVEL%
)
echo.
echo Panel V4.0 generado con exito. Abriendo en el navegador...
start "" index_v4_0.html
