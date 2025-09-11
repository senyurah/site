@echo off
cd /d %~dp0downloads\server
..\..\venv\Scripts\python.exe dashboard_server.py
pause
