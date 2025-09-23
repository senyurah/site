@echo off
cd /d %~dp0ddos\client
..\venv\Scripts\python.exe send_images_infinite.py
pause
