# Multi-stage Dockerfile for TTS Microservice

# Build stage
FROM python:3.11-slim as builder

# Install system dependencies for audio processing
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    ffmpeg \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --user -r requirements.txt

# Production stage
FROM python:3.11-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash tts

# Set working directory
WORKDIR /app

# Copy Python packages from builder stage
COPY --from=builder /root/.local /home/tts/.local

# Copy application code
COPY app/ ./app/
COPY config.yaml .

# Set ownership
RUN chown -R tts:tts /app

# Switch to non-root user
USER tts

# Make sure scripts in .local are usable
ENV PATH=/home/tts/.local/bin:$PATH

# Expose ports
EXPOSE 8000 9090

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/v1/tts/health')"

# Run the application
CMD ["python", "-m", "app.main"]