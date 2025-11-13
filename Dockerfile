# Use Python 3.11 slim image
FROM python:3.11-slim

# Install system deps for Playwright
RUN apt-get update && apt-get install -y wget curl unzip libnss3 libatk-bridge2.0-0 libxkbcommon0 libgtk-3-0 libdrm2 libgbm1 libasound2 libxdamage1 libxfixes3 libxrandr2 libpango-1.0-0 libcairo2 fonts-liberation libappindicator3-1 libxshmfence1 && apt-get clean

# Set working directory
WORKDIR /app

# Copy files
COPY . /app

# Install Python deps
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright Chromium
RUN playwright install --with-deps chromium

# Expose Railway/Render PORT
ENV PORT=8000

# Command to start server
CMD ["sh", "-c", "uvicorn api:app --host 0.0.0.0 --port ${PORT:-8000} --timeout-keep-alive 75"]
