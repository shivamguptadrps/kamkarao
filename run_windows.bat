@echo off
REM Start KamKarao on your laptop. Open http://127.0.0.1:8000 in the browser.
cd /d "%~dp0"
call .venv\Scripts\activate.bat
start "" http://127.0.0.1:8000/
python manage.py runserver 0.0.0.0:8000
