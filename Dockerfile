# Base image
FROM python:3.11-slim

# Set environment
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# Install system dependencies for Playwright/Chromium
RUN apt-get update && apt-get install -y \
    wget curl unzip libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 \
    libxkbcommon0 libxcomposite1 libxrandr2 libxdamage1 libgbm-dev \
    libpango-1.0-0 libasound2 libxshmfence1 libx11-xcb1 libgtk-3-0 \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright Chromium (headless)
RUN playwright install --with-deps chromium

# Copy all project files
COPY . .

# Expose Railway dynamic port (fallback to 8000 if not set)
EXPOSE ${PORT:-8000}

# ✅ Start FastAPI app (Railway-compatible)
CMD ["sh", "-c", "uvicorn api:app --host 0.0.0.0 --port ${PORT:-8000} --timeout-keep-alive 75"]
