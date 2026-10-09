@echo off
title Actualizar Panel Garmin
echo ========================================================
echo Actualizando Panel de Entrenamiento Garmin...
echo ========================================================
set "PATH=C:\Users\emili\.local\bin;%PATH%"
set "GARMINTOKENS=C:\Users\emili\.garminconnect"
cd /d "d:\Archivos personales\Apps Antigravity\garmin_mcp"
uv run python dashboard.py
echo.
echo ========================================================
echo Abriendo index.html en tu navegador...
echo ========================================================
start index.html
