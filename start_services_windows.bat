@echo off
REM Start FastAPI (using uvicorn)
start "FastAPI" python -m uvicorn main:app --host 0.0.0.0 --port 8000

REM Start Gradio UI
start "Gradio" python gradio_demo.py --server.port 7860 --server.host 0.0.0.0

REM Wait for user to close both windows
echo Both services started. Press any key to exit this script.
pause
