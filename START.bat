@echo off
echo.
echo ========================================
echo   PHI Redaction Tool — Starting Backend
echo ========================================
echo.
cd /d "%~dp0backend"
pip install -r requirements.txt --quiet
echo Starting FastAPI server on http://127.0.0.1:8000 ...
echo Open frontend\index.html in your browser.
echo Press Ctrl+C to stop.
echo.
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
pause
