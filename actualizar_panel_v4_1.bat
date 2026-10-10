@echo off
chcp 65001 > nul
echo ====================================================================
echo   GARMIN PERFORMANCE LAB V4.1 - SINCRONIZACIÓN Y ACTUALIZACIÓN
echo ====================================================================
echo.
echo Descargando telemetría oficial de Garmin Connect y Forerunner 265...
echo Generando panel interactivo index_v4_1.html...
echo.

uv run python dashboard_v4_1.py

if %ERRORLEVEL% equ 0 (
    echo.
    echo ====================================================================
    echo  [OK] Panel V4.1 generado exitosamente en:
    echo       d:\Archivos personales\Apps Antigravity\garmin_mcp\index_v4_1.html
    echo ====================================================================
    start index_v4_1.html
) else (
    echo.
    echo [ERROR] Hubo un problema al ejecutar dashboard_v4_1.py.
)
pause
