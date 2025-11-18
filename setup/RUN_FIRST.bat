@echo off
echo ================================================
echo         AROGYA AI - Auto Setup Script
echo ================================================
echo.

REM Check Python Version
python --version
IF %ERRORLEVEL% NEQ 0 (
    echo Python is not installed. Please install Python 3.10 or 3.11
    pause
    exit /b
)

echo Creating Virtual Environment...
python -m venv venv

echo Activating Virtual Environment...
call venv\Scripts\activate

echo Upgrading pip...
pip install --upgrade pip setuptools wheel

echo Installing Required Modules...
pip install -r requirements.txt

echo Setting up MySQL Database...
python setup\auto_import_dataset.py

echo Starting Arogya AI...
python app.py

echo ---------------------------------------------
echo  Setup Complete! Arogya AI is now running.
echo  Open your browser and visit:
echo      http://127.0.0.1:5000
echo ---------------------------------------------
pause

