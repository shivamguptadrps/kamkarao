@echo off
REM Unattended setup: installs packages, builds the database, loads demo data, creates the admin login.
REM Progress is written to setup_log.txt in this folder.
cd /d "%~dp0"
set LOG=setup_log.txt
echo === KamKarao setup %date% %time% === > %LOG%
set PY=
where py >nul 2>nul && set PY=py -3
if "%PY%"=="" where python >nul 2>nul && set PY=python
if "%PY%"=="" (echo PYTHON_NOT_FOUND >> %LOG% & exit /b 1)
%PY% --version >> %LOG% 2>&1 || (echo PYTHON_NOT_WORKING >> %LOG% & exit /b 1)
if not exist .venv %PY% -m venv .venv >> %LOG% 2>&1
call .venv\Scripts\activate.bat || (echo VENV_FAILED >> %LOG% & exit /b 1)
python -m pip install --upgrade pip >> %LOG% 2>&1
pip install -r requirements.txt >> %LOG% 2>&1 || (echo PIP_FAILED >> %LOG% & exit /b 1)
if not exist .env copy .env.example .env >nul
python manage.py migrate >> %LOG% 2>&1 || (echo MIGRATE_FAILED >> %LOG% & exit /b 1)
python manage.py seed_demo >> %LOG% 2>&1 || (echo SEED_FAILED >> %LOG% & exit /b 1)
set DJANGO_SUPERUSER_USERNAME=admin
set DJANGO_SUPERUSER_EMAIL=admin@kamkarao.com
set DJANGO_SUPERUSER_PASSWORD=KK-HslvVZg5XEvl
python manage.py createsuperuser --noinput >> %LOG% 2>&1
echo SETUP_OK >> %LOG%
