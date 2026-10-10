@echo off
chcp 65001 > nul
echo ===================================================
echo   Garmin Performance Lab - Actualizando a V3.3
echo ===================================================
echo Sincronizando metricas Garmin, KPIs en 1 linea, Predicciones, Estado de Entreno y Z2...
call uv run python dashboard_v3_3.py
if %ERRORLEVEL% NEQ 0 (
    echo Error al actualizar el panel V3.3. Revisa tu conexion o sesion.
    pause
    exit /b %ERRORLEVEL%
)
echo.
echo Panel V3.3 generado con exito. Abriendo en el navegador...
start "" index_v3_3.html
