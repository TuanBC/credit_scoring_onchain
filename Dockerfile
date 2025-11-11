FROM python:3.12-slim AS base

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
		build-essential \
		&& rm -rf /var/lib/apt/lists/*

# Copy requirements first for cache efficiency
COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip && \
		pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN useradd -m appuser
USER appuser

# Expose FastAPI and Gradio ports
EXPOSE 8000
EXPOSE 7860

# Make process manager script executable
RUN chmod +x /app/start_services.sh

# Healthcheck (optional, for FastAPI)
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
	CMD curl -f http://localhost:8000/ || exit 1

# Start both services
CMD ["/bin/bash", "/app/start_services.sh"]
