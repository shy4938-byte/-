@echo off
cd /d "%~dp0"
python -m pip install -r requirements.txt
if errorlevel 1 exit /b 1
set QT_QPA_PLATFORM=offscreen
python -m unittest discover -s tests -v
if errorlevel 1 exit /b 1
python build_windows.py
