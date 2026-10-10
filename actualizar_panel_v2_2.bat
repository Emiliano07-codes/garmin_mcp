@echo off
title Generar y Abrir Panel Garmin V2.2
echo ========================================================
echo Generando Panel Garmin Versión 2.2 (Crosshair + KPIs Interactivos)...
echo ========================================================
set "PATH=C:\Users\emili\.local\bin;%PATH%"
set "GARMINTOKENS=C:\Users\emili\.garminconnect"
cd /d "d:\Archivos personales\Apps Antigravity\garmin_mcp"
uv run python dashboard_v2_2.py
echo.
echo ========================================================
echo Abriendo index_v2_2.html en tu navegador...
echo ========================================================
start index_v2_2.html
