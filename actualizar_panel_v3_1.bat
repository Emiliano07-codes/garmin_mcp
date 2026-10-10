@echo off
chcp 65001 > nul
echo ===================================================
echo   Garmin Performance Lab - Actualizando a V3.1
echo ===================================================
echo Sincronizando metricas Garmin, historial completo y Estado de Entreno...
call uv run python dashboard_v3_1.py
if %ERRORLEVEL% NEQ 0 (
    echo Error al actualizar el panel V3.1. Revisa tu conexion o sesion.
    pause
    exit /b %ERRORLEVEL%
)
echo.
echo Panel V3.1 generado con exito. Abriendo en el navegador...
start "" index_v3_1.html
