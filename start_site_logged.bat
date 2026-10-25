@echo off
REM Starts the site and writes server output to server_log.txt
cd /d "%~dp0"
call .venv\Scripts\activate.bat
start "" http://127.0.0.1:8000/
python manage.py runserver 0.0.0.0:8000 > server_log.txt 2>&1
