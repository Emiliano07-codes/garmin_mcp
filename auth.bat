@echo off
title Garmin Connect Auth
echo ==============================================
echo Iniciando autenticacion de Garmin MCP...
echo ==============================================
set "PATH=C:\Users\emili\.local\bin;%PATH%"
cd /d "d:\Archivos personales\Apps Antigravity\garmin_mcp"
uv run garmin-mcp-auth
pause
