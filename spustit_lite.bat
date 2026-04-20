@echo off
setlocal
chcp 65001 >nul

cd /d "%~dp0"

set "PORT=8015"

if not exist ".venv\Scripts\python.exe" (
    echo .venv nebylo nalezeno, vytvarim virtualni prostredi...
    py -m venv .venv
    if errorlevel 1 (
        echo Nepodarilo se vytvorit .venv
        pause
        exit /b 1
    )

    echo Instaluji balicky...
    .venv\Scripts\python.exe -m pip install -r requirements-runtime.txt
    if errorlevel 1 (
        echo Nepodarilo se nainstalovat requirements.txt
        pause
        exit /b 1
    )
)

echo [1/2] Generuji aktualni predikce pro frontend...
.venv\Scripts\python.exe -m src.predict --export-upcoming-json --rounds-ahead 2
if errorlevel 1 (
    echo Export predikci selhal.
    pause
    exit /b 1
)

echo [2/2] Spoustim frontend na http://localhost:%PORT%/.lib/
start "" "http://localhost:%PORT%/.lib/"
.venv\Scripts\python.exe -m http.server %PORT%

endlocal
