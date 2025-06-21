# Use a Node.js base image with Python support for Railway
FROM node:18-bullseye

# Install system dependencies including Chrome
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    wget \
    gnupg \
    ca-certificates \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libatspi2.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxkbcomposite0 \
    libxrandr2 \
    xdg-utils \
    dbus \
    dbus-x11 \
    xvfb \
    && rm -rf /var/lib/apt/lists/*

# Install Google Chrome for whatsapp-web.js
RUN wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Copy package files first (for better Docker layer caching)
COPY package*.json ./

# Install Node.js dependencies
RUN npm ci --only=production

# Copy Python requirements
COPY requirements.txt ./

# Install Python dependencies
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . .

# Create necessary directories with proper permissions
RUN mkdir -p /app/.wwebjs_auth /app/.wwebjs_cache /app/tokens \
    && chmod -R 755 /app/.wwebjs_auth /app/.wwebjs_cache /app/tokens

# Set environment variables for cloud deployment
ENV NODE_ENV=production
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV DISPLAY=:99
ENV PUPPETEER_SKIP_CHROMIUM_DOWNLOAD=true
ENV PUPPETEER_EXECUTABLE_PATH=/usr/bin/google-chrome-stable

# Create startup script for Railway
RUN echo '#!/bin/bash\n\
echo "🚀 Starting Smart WhatsApp Booking Bot on Railway..."\n\
\n\
# Start virtual display for headless Chrome\n\
Xvfb :99 -screen 0 1024x768x24 > /dev/null 2>&1 &\n\
\n\
# Start WhatsApp Web service in background\n\
echo "📱 Starting WhatsApp Web service..."\n\
node whatsapp-service.js &\n\
WHATSAPP_PID=$!\n\
echo "WhatsApp Web service started with PID: $WHATSAPP_PID"\n\
\n\
# Wait for WhatsApp service to initialize\n\
sleep 5\n\
\n\
# Start FastAPI application\n\
echo "🚀 Starting FastAPI backend..."\n\
python3 -m uvicorn app.main:app --host 0.0.0.0 --port $PORT\n\
' > /app/start-railway.sh && chmod +x /app/start-railway.sh

# Health check endpoint for Railway
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:$PORT/health || exit 1

# Expose the port (Railway will set the PORT environment variable)
EXPOSE $PORT

# Use the Railway startup script
CMD ["/app/start-railway.sh"] 