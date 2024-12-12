# Build stage
FROM python:3.11-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /app/wheels -r requirements.txt

# Final stage
FROM python:3.11-slim

# Create non-root user
RUN useradd -m -u 1000 appuser

# Install Redis
RUN apt-get update && apt-get install -y --no-install-recommends \
    redis-server \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy wheels from builder
COPY --from=builder /app/wheels /wheels
COPY --from=builder /app/requirements.txt .

# Install dependencies
RUN pip install --no-cache /wheels/*

# Copy the entire project
COPY . /app/

# Install our package in development mode
RUN pip install -e .

# Set ownership
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Copy startup script
COPY --chown=appuser:appuser scripts/start.sh /app/start.sh
RUN chmod +x /app/start.sh

# Add src directory to Python path
ENV PYTHONPATH=/app/src:$PYTHONPATH

# Expose Redis port (optional, only if you need external access)
EXPOSE 6379

# Start both Redis and the application
CMD ["/app/start.sh"]
