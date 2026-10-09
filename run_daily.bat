@echo off
rem 작업 스케줄러가 평일 08:00에 실행: 브리핑 전송 + 신문 게시 + 신문 페이지 열기
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
echo ===== %date% %time% >> data\run.log
"C:\Users\user\AppData\Local\Python\pythoncore-3.14-64\python.exe" main.py --publish >> data\run.log 2>&1
if %errorlevel%==0 start "" https://ckurusa.github.io/news-briefing/
