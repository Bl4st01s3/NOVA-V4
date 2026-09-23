@echo off
echo ==========================================
echo          Starting NOVA AI Assistant
echo ==========================================

echo Starting LM Studio (Bionic) Server in the background...
:: Using start /B to run it in the background of the same window, or just start to open a new window.
:: Opening a new window for the server is often safer so the user can see server logs.
start "LM Studio Server" cmd /c "lms server start"

echo Waiting a few seconds for the server to spin up...
timeout /t 5 /nobreak > NUL

echo Checking dependencies...
call venv\Scripts\activate.bat
pip install -r requirements.txt -q

echo Starting NOVA UI...
:: pythonw runs the script without a terminal window popup
start pythonw main.py
