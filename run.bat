@echo off
echo ==========================================
echo          Starting NOVA AI Assistant
echo ==========================================

echo Starting LM Studio (Bionic) Server...
:: Since launch_nova.vbs hides the main batch window, we must use /B here
:: to prevent 'start' from spawning a brand new, visible command window
:: for the LM Studio background process.
start /B "LM Studio Server" cmd /c "lms server start"

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
