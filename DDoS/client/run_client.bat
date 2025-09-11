@echo off
cd /d %~dp0downloads\client
..\..\venv\Scripts\python.exe send_images_infinite.py
pause
