@echo off
echo.
echo ========================================
echo   PHI Redaction Tool — Starting Backend
echo ========================================
echo.
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -m pip install -r files\requirements.txt --quiet
) else (
    python -m pip install -r files\requirements.txt --quiet
)
echo Starting FastAPI server on http://127.0.0.1:8000 ...
echo Open files\index.html in your browser.
echo Press Ctrl+C to stop.
echo.
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
) else (
    python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
)
pause
