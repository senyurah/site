@echo off
cd /d %~dp0ddos\server
..\venv\Scripts\python.exe dashboard_server.py
pause
