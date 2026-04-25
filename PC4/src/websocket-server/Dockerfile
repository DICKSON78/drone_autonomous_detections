# WebSocket Server Dockerfile
# Node.js 20 with Kafka listener for real-time event relay

FROM node:20-slim

WORKDIR /app

# Install curl for health checks
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci --only=production

# Copy application code
COPY server.js kafka_listener.js message_handler.js client_manager.js ./

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8006/health || exit 1

# Default environment
ENV WS_PORT=8006 \
    KAFKA_BROKER=kafka:9092 \
    NODE_ENV=production

# Expose WebSocket port
EXPOSE 8006

# Run server
CMD ["node", "server.js"]
