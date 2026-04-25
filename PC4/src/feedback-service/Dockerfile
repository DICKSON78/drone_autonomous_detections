# Feedback Service Dockerfile
# Python 3.10 with espeak-ng for TTS support

FROM python:3.10-slim

WORKDIR /app

# Install system dependencies for audio and TTS
RUN apt-get update && apt-get install -y --no-install-recommends \
    espeak-ng \
    alsa-utils \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY feedback.py tts_engine.py audio_manager.py message_queue.py ./

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8005/health || exit 1

# Default environment variables
ENV TTS_RATE=150 \
    TTS_VOLUME=1.0 \
    TTS_VOICE_INDEX=0 \
    PORT=8005

# Run FastAPI server
CMD ["python", "feedback.py"]
