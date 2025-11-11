#!/bin/bash
set -e
# Start FastAPI (production: gunicorn with uvicorn worker)
gunicorn main:app --workers 4 --bind 0.0.0.0:8000 --worker-class uvicorn.workers.UvicornWorker &
# Start Gradio UI
timeout 5 python gradio_demo.py --server.port 7860 --server.host 0.0.0.0 &
wait
