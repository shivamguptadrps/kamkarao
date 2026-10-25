@echo off
cd /d "%~dp0"
echo started %date% %time% > check_log.txt
.venv\Scripts\python.exe -c "import urllib.request as u; r=u.urlopen('http://127.0.0.1:8000/hi/', timeout=5); print('SITE_UP', r.status)" >> check_log.txt 2>&1
netstat -ano | findstr :8000 >> check_log.txt
