@echo off
rem Start SWE Practice: creates the virtual environment on first run, then opens the app.
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo First run: creating virtual environment...
    python -m venv .venv || goto :error
    ".venv\Scripts\python.exe" -m pip install --upgrade pip || goto :error
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt || goto :error
)
".venv\Scripts\python.exe" -m swe_prac %*
goto :eof

:error
echo.
echo Setup failed. Make sure Python 3.12+ is installed and on PATH.
pause
