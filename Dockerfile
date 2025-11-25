
FROM python:3.14-slim

WORKDIR /app

# Install system dependencies and uv
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    make \
    cmake \
    && rm -rf /var/lib/apt/lists/*

# Install uv using the official binary installer

RUN curl -LsSf https://astral.sh/uv/install.sh | sh

# Add uv to PATH
ENV PATH="/root/.local/bin:$PATH"


# Copy requirements first for better caching
COPY requirements.txt .
COPY pyproject.toml .
COPY uv.lock .

# Install Python dependencies using uv
# Use --no-install-project to install dependencies without requiring the source code yet
RUN uv sync --frozen --no-install-project

# Add virtual environment to PATH
ENV PATH="/app/.venv/bin:$PATH"

# Copy application code
COPY . .


# Secrets and environment variables should be injected by AWS ECS (do not bake .env into image)

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

