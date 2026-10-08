@echo off
echo ==========================================
echo       Setting up NOVA AI Assistant
echo ==========================================

echo [1/3] Creating Python Virtual Environment...
python -m venv venv

echo [2/3] Activating Virtual Environment...
call venv\Scripts\activate.bat

echo [3/3] Installing Dependencies...
pip install -r requirements.txt

echo [4/4] Downloading Default Piper TTS Model...
python download_piper_models.py

echo ==========================================
echo Setup Complete! You can now run run.bat
echo ==========================================
pause
