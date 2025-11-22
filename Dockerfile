
FROM python:3.14-slim

WORKDIR /app

# Install system dependencies and uv
RUN apt-get update && apt-get install -y \
    gcc \
    && pip install uv \
    && rm -rf /var/lib/apt/lists/*


# Copy requirements first for better caching
COPY requirements.txt .
COPY pyproject.toml .

# Install Python dependencies using uv
RUN uv sync

# Copy application code
COPY . .

# Copy .env file if present
COPY .env .env

# Create necessary directories
RUN mkdir -p app/static/css app/static/js app/templates

# Set environment variable for production
ENV ENVIRONMENT=production

# Expose port
EXPOSE 8000

# Health check using built-in Python modules
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')"

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

