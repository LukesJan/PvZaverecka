@echo off
setlocal
chcp 65001 >nul

cd /d "%~dp0"

set "PORT=8015"
set "PYTHON_CMD="
set "VENV_PYTHON=.venv\Scripts\python.exe"

echo.
echo ==== Spusteni projektu ====
echo.

REM 1) Najdi systemovy Python, pokud neni .venv
if exist "%VENV_PYTHON%" (
    set "PYTHON_CMD=%VENV_PYTHON%"
    goto :python_ready
)

py -3 --version >nul 2>&1
if not errorlevel 1 (
    set "PYTHON_CMD=py -3"
    goto :create_venv
)

python --version >nul 2>&1
if not errorlevel 1 (
    set "PYTHON_CMD=python"
    goto :create_venv
)

echo Chyba: Python nebyl nalezen.
echo.
echo Nainstaluj Python 3 a zkus to znovu.
echo.
pause
exit /b 1

:create_venv
echo [Priprava] Virtualni prostredi .venv nebylo nalezeno.
echo [Priprava] Vytvarim .venv...
%PYTHON_CMD% -m venv .venv
if errorlevel 1 (
    echo.
    echo Chyba: nepodarilo se vytvorit virtualni prostredi.
    echo.
    pause
    exit /b 1
)

set "PYTHON_CMD=%VENV_PYTHON%"

echo [Priprava] Aktualizuji pip...
%PYTHON_CMD% -m pip install --upgrade pip
if errorlevel 1 (
    echo.
    echo Upozorneni: pip se nepodarilo aktualizovat, pokracuji se stavajici verzi.
)

if not exist "requirements-runtime.txt" (
    echo.
    echo Chyba: chybi requirements-runtime.txt
    echo.
    pause
    exit /b 1
)

if exist "offline_packages\*.whl" (
    echo [Priprava] Instaluji balicky offline ze slozky offline_packages...
    %PYTHON_CMD% -m pip install --no-index --find-links "offline_packages" -r requirements-runtime.txt
) else (
    echo [Priprava] Instaluji balicky z internetu...
    %PYTHON_CMD% -m pip install -r requirements-runtime.txt
)
if errorlevel 1 (
    echo.
    echo Chyba: nepodarilo se nainstalovat balicky.
    echo.
    echo Pokud jsi na skolnim pocitaci bez internetu, priprav doma offline balicky:
    echo   priprav_offline_balicky.bat
    echo Potom zkopiruj celou slozku offline_packages do projektu ve skole
    echo a spust:
    echo   nainstaluj_offline_balicky.bat
    echo.
    pause
    exit /b 1
)

goto :checks

:python_ready
echo [Info] Pouzivam existujici .venv

:checks
echo [Info] Python: %PYTHON_CMD%

REM 2) Over zakladni balicky
echo.
echo [Kontrola] Overuji Python balicky...
%PYTHON_CMD% -c "import pandas, numpy, joblib, sklearn, dotenv" >nul 2>&1
if errorlevel 1 (
    echo Chyba: chybi nektere balicky.
    if exist "offline_packages\*.whl" (
        echo Pokousim se je doinstalovat offline ze slozky offline_packages...
        %PYTHON_CMD% -m pip install --no-index --find-links "offline_packages" -r requirements-runtime.txt
    ) else (
        echo Pokousim se je doinstalovat z internetu...
        %PYTHON_CMD% -m pip install -r requirements-runtime.txt
    )
    if errorlevel 1 (
        echo.
        echo Chyba: instalace balicku selhala.
        echo Na skolnim PC pravdepodobne nejde stahovat z internetu.
        echo Pouzij offline postup: priprav_offline_balicky.bat doma a nainstaluj_offline_balicky.bat ve skole.
        echo.
        pause
        exit /b 1
    )
)

REM 3) Kontrola modelu
echo.
echo [Kontrola] Overuji modely...
if not exist "models" (
    echo Chyba: chybi slozka models.
    echo Nejdriv je potreba mit natrenovane modely.
    echo.
    pause
    exit /b 1
)

dir /b "models\*.joblib" >nul 2>&1
if errorlevel 1 (
    echo Chyba: ve slozce models nebyl nalezen zadny .joblib soubor.
    echo Nejdriv spust training.ipynb a uloz modely.
    echo.
    pause
    exit /b 1
)

REM 4) Kontrola raw dat
echo.
echo [Kontrola] Overuji raw data...
if not exist "data\raw" (
    echo Chyba: chybi slozka data\raw
    echo.
    pause
    exit /b 1
)

dir /b "data\raw\*_fixtures.csv" >nul 2>&1
if errorlevel 1 (
    echo Chyba: v data\raw nejsou soubory *_fixtures.csv
    echo.
    echo Pro export predikci jsou raw data potreba.
    echo .env je nutny hlavne pri stahovani novych dat z API-Football.
    echo.
    pause
    exit /b 1
)

REM 5) Vygeneruj JSON
echo.
echo [1/2] Generuji aktualni predikce pro frontend...
%PYTHON_CMD% -m src.predict --export-upcoming-json --rounds-ahead 2
if errorlevel 1 (
    echo.
    echo Export predikci selhal.
    echo Zkontroluj modely, raw data a nainstalovane balicky.
    echo.
    pause
    exit /b 1
)

if not exist "data\processed\upcoming_predictions.json" (
    echo.
    echo Chyba: nebyl vytvoren soubor data\processed\upcoming_predictions.json
    echo.
    pause
    exit /b 1
)

REM 6) Spust frontend
echo.
echo [2/2] Spoustim frontend na http://localhost:%PORT%/.lib/
start "" "http://localhost:%PORT%/.lib/"
%PYTHON_CMD% -m http.server %PORT%

endlocal
