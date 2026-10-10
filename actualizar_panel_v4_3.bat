@echo off
chcp 65001 > nul
echo =======================================================
echo Actualizando Garmin Performance Lab V4.3
echo Atleta: Emiliano
echo =======================================================
cd /d "%~dp0"
uv run python dashboard_v4_3.py
echo.
echo Presiona una tecla para abrir el panel generado...
pause > nul
start index_v4_3.html
