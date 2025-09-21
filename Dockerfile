# Use lightweight Python base
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Disable Python buffering & warnings
ENV PYTHONUNBUFFERED=1
ENV PYTHONWARNINGS="ignore"

# Install system deps (for pandas/numpy/web3)
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    libssl-dev \
    libffi-dev \
    python3-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install pip latest
RUN pip install --upgrade pip setuptools wheel

# Copy requirements first (better caching)
COPY requirements.txt .

# Install Python deps
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Default command (runs bot.py)
CMD ["python", "bot.py"]
