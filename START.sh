#!/bin/bash
echo ""
echo "========================================"
echo "  PHI Redaction Tool — Starting Backend"
echo "========================================"
echo ""

cd "$(dirname "$0")"

# Install dependencies if needed
if [ -x ".venv/bin/python" ]; then
  ".venv/bin/python" -m pip install -r files/requirements.txt --quiet
else
  python -m pip install -r files/requirements.txt --quiet
fi

echo "Starting FastAPI server on http://127.0.0.1:8000 ..."
echo "Open files/index.html in your browser."
echo "Press Ctrl+C to stop."
echo ""

if [ -x ".venv/bin/python" ]; then
  ".venv/bin/python" -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
else
  python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
fi
