@echo off
title Football AI Predictor
echo ==========================================
echo Starting server
echo ==========================================
echo.

cd /d "%~dp0"

set PYTHONPATH=%cd%
set PORT=8015
set PYTHON=.venv\Scripts\python.exe

if not exist "%PYTHON%" (
    set PYTHON=python
)

echo Generating predictions...
%PYTHON% -m src.predict --export-upcoming-json --rounds-ahead 2
if errorlevel 1 (
    echo.
    echo Prediction export failed.
    echo Check that packages are installed and models/data exist.
    echo.
    pause
    exit /b 1
)

echo.
echo Opening frontend...
start http://127.0.0.1:%PORT%/

echo.
echo Server running at http://127.0.0.1:%PORT%/
echo Press Ctrl+C to stop the server.
echo.

%PYTHON% -m http.server %PORT%

pause
