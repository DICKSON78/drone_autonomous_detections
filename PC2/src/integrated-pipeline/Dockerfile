FROM python:3.10-slim

# Install basic system dependencies for Jupyter
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    python3-dev \
    wget \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Install only Jupyter for Colab connection
RUN pip install jupyterlab --no-cache-dir

# Create necessary directories
RUN mkdir -p /app/models /app/data /app/logs /app/config /workspace

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8004

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8004/health || exit 1

CMD ["python", "main_pipeline.py"]
