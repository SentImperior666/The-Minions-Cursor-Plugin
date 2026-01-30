# Dockerfile for The Minions Cursor Plugin - Development/Testing
# Task 3: Redis Database Interface and CodebaseIndexer

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for caching
COPY requirements.txt requirements-dev.txt ./

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements-dev.txt

# Copy source code
COPY src/ ./src/
COPY tests/ ./tests/

# Set Python path
ENV PYTHONPATH=/app

# Default command: run tests
CMD ["pytest", "-v", "--cov=src", "--cov-report=term-missing"]
