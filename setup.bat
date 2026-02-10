@echo off
REM Quick Start Script for Quality Management System (Windows)

echo ==================================
echo Quality Management System Setup
echo ==================================
echo.

REM Check Python version
echo Checking Python version...
python --version

if %errorlevel% neq 0 (
    echo ERROR: Python is not installed or not in PATH!
    echo Please install Python 3.10 or higher from python.org
    pause
    exit /b 1
)

echo.
echo Creating virtual environment...
python -m venv env

echo.
echo Activating virtual environment...
call env\Scripts\activate.bat

echo.
echo Installing dependencies...
python -m pip install --upgrade pip
pip install -r requirements.txt

echo.
echo ==================================
echo Setup Complete!
echo ==================================
echo.
echo To run the application:
echo   1. Activate virtual environment: env\Scripts\activate
echo   2. Run application: python main.py
echo.
echo Default login credentials:
echo   Username: admin
echo   Password: admin123
echo.
echo IMPORTANT: Change the default password after first login!
echo.
pause
