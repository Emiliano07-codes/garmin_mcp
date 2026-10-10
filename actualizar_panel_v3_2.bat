@echo off
chcp 65001 > nul
echo ===================================================
echo   Garmin Performance Lab - Actualizando a V3.2
echo ===================================================
echo Sincronizando metricas Garmin, menu lateral y jerarquia visual...
call uv run python dashboard_v3_2.py
if %ERRORLEVEL% NEQ 0 (
    echo Error al actualizar el panel V3.2. Revisa tu conexion o sesion.
    pause
    exit /b %ERRORLEVEL%
)
echo.
echo Panel V3.2 generado con exito. Abriendo en el navegador...
start "" index_v3_2.html
