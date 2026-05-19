FROM python:3.10-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose ports (MAVLink and API)
EXPOSE 8001
EXPOSE 14540/udp

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=8001

# Run the Python flight controller
CMD ["python", "flight_controller.py"]