@echo off
title Generar y Abrir Panel Garmin V3.0 (Strava Engine)
echo ========================================================
echo Generando Panel Garmin Versión 3.0 (Módulo Strava + Cockpit)...
echo ========================================================
set "PATH=C:\Users\emili\.local\bin;%PATH%"
set "GARMINTOKENS=C:\Users\emili\.garminconnect"
cd /d "d:\Archivos personales\Apps Antigravity\garmin_mcp"
uv run python dashboard_v3_0.py
echo.
echo ========================================================
echo Abriendo index_v3_0.html en tu navegador...
echo ========================================================
start index_v3_0.html
