# Use Python 3.11 slim image
FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# ✅ Pass environment variable into container
ENV OPENAI_API_KEY=${OPENAI_API_KEY}

# Install system dependencies (for Playwright)
RUN apt-get update && apt-get install -y \
    wget curl unzip libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 \
    libxkbcommon0 libxcomposite1 libxrandr2 libxdamage1 libgbm-dev \
    libpango-1.0-0 libasound2 libxshmfence1 libx11-xcb1 libgtk-3-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers
RUN playwright install --with-deps chromium

# Copy project files
COPY . .

EXPOSE 8000

# ✅ Start the FastAPI app
CMD ["sh", "-c", "uvicorn api:app --host 0.0.0.0 --port ${PORT:-8000}"]
