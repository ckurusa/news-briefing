@echo off
rem Daily 08:00 via Task Scheduler: send briefing, publish paper, open page
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
echo ===== %date% %time% >> data\run.log
"C:\Users\user\AppData\Local\Python\pythoncore-3.14-64\python.exe" main.py --publish >> data\run.log 2>&1
if %errorlevel%==0 start "" https://ckurusa.github.io/news-briefing/
