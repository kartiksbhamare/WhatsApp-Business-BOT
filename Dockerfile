# Multi-stage build for production
FROM node:18-bullseye-slim AS base

# Install system dependencies for Chrome and Python
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    ca-certificates \
    curl \
    python3 \
    python3-pip \
    python3-venv \
    && rm -rf /var/lib/apt/lists/*

# Install Chrome
RUN wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# Set Chrome environment variables
ENV PUPPETEER_SKIP_CHROMIUM_DOWNLOAD=true
ENV PUPPETEER_EXECUTABLE_PATH=/usr/bin/google-chrome-stable

# Set working directory
WORKDIR /app

# Copy package files
COPY package*.json ./
COPY requirements.txt ./

# Install Node.js dependencies
RUN npm ci --only=production

# Install Python dependencies
RUN python3 -m pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p .wwebjs_auth .wwebjs_cache tokens

# Set permissions
RUN chmod +x start*.sh run*.sh

# Environment variables with defaults
ENV NODE_ENV=production
ENV BACKEND_HOST=0.0.0.0
ENV BACKEND_PORT=8000
ENV WHATSAPP_HOST=0.0.0.0
ENV WHATSAPP_PORT=3000
ENV SALON_NAME="Beauty Salon"

# Expose ports
EXPOSE ${BACKEND_PORT}
EXPOSE ${WHATSAPP_PORT}

# Health check using environment variable
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:${BACKEND_PORT:-8000}/health || exit 1

# Default command (can be overridden in docker-compose)
CMD ["node", "whatsapp-simple.js"] 