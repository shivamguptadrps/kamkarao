@echo off
REM One-time setup on Windows. Double-click or run from this folder.
cd /d "%~dp0"
echo.
echo === KamKarao setup ===
where py >nul 2>nul && (set PY=py -3) || (set PY=python)
%PY% --version || (echo Python not found. Install Python 3.12 from python.org and tick "Add to PATH". & pause & exit /b 1)

if not exist .venv (
  echo Creating virtual environment...
  %PY% -m venv .venv
)
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt || (echo Package install failed. & pause & exit /b 1)

if not exist .env copy .env.example .env >nul

python manage.py migrate
python manage.py seed_demo
echo.
echo Now create your admin login (choose a username and password):
python manage.py createsuperuser
echo.
echo Setup complete. Run run_windows.bat to start the site.
pause
