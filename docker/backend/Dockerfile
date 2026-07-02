FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY docker/backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source
COPY PC3/desktop/backend/server.py .
COPY PC3/desktop/backend/telemetry_store.py .

# Copy NLP module
RUN mkdir -p /app/nlp
COPY PC2/src/nlp_module.py /app/nlp/

# Copy frontend static files
COPY PC3/desktop/renderer/ ./renderer/

EXPOSE 8007

ENV TELEMETRY_DB_PATH=/data/telemetry.db

CMD ["python3", "server.py"]
