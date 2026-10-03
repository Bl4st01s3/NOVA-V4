@echo off
echo ==========================================
echo          Starting NOVA AI Assistant
echo ==========================================

echo Starting LM Studio (Bionic) Server...
:: We do NOT use 'start /B' here anymore, because this entire batch script
:: will be launched invisibly by launch_nova.vbs. However, 'start' alone
:: ensures the lms server is a detached process that won't hold up the python script.
start "LM Studio Server" /MIN cmd /c "lms server start"

echo Waiting a few seconds for the server to spin up...
timeout /t 5 /nobreak > NUL

echo Pre-loading Llama 3.1 8B into the GPU for maximum speed...
lms load --gpu max "llama-3.1-8b-instruct" --yes

echo Checking dependencies...
call venv\Scripts\activate.bat
pip install -r requirements.txt -q

echo Starting NOVA UI...
:: pythonw runs the script without a terminal window popup
start pythonw main.py
