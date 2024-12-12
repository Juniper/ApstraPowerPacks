#!/bin/bash
set -e

# Start Redis in the background
redis-server --daemonize yes

# Wait for Redis to be ready
until redis-cli ping > /dev/null 2>&1; do
  echo "Waiting for Redis..."
  sleep 1
done

# Start the main application
python3 -m src.main
