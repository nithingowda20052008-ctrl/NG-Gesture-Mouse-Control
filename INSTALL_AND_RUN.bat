@echo off
title NG Gesture Mouse Control Setup
cd /d "%~dp0"
echo Checking Python...
py -3.11 --version
if errorlevel 1 (
  echo.
  echo Python 3.11 was not found.
  echo Install Python 3.11 64-bit and select "Add Python to PATH".
  pause
  exit /b 1
)
if not exist .venv (
  echo Creating virtual environment...
  py -3.11 -m venv .venv
)
call .venv\Scripts\activate.bat
echo Installing required packages...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if errorlevel 1 (
  echo.
  echo Installation failed. Check your internet connection and Python version.
  pause
  exit /b 1
)
echo.
echo Setup complete. Starting NG Gesture Mouse Control...
python src\gesture_mouse.py
pause
