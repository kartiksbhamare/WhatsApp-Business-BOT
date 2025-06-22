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
    libxkbcommon0 \
    libxrandr2 \
    xdg-utils \
    dbus \
    dbus-x11 \
    xvfb \
    curl \
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

# Create startup script for Railway with REAL WhatsApp Web.js service
RUN echo '#!/bin/bash\n\
echo "🚀 Starting Smart WhatsApp Booking Bot with PRODUCTION WhatsApp Integration on Railway..."\n\
\n\
# Create Firebase credentials file from environment variable\n\
if [ ! -z "$FIREBASE_KEY_JSON" ]; then\n\
    echo "📝 Creating Firebase credentials file..."\n\
    echo "$FIREBASE_KEY_JSON" > /app/firebase-key.json\n\
    echo "✅ Firebase credentials file created"\n\
else\n\
    echo "⚠️ Warning: FIREBASE_KEY_JSON environment variable not set"\n\
fi\n\
\n\
# Start virtual display for headless Chrome\n\
echo "🖥️ Starting virtual display..."\n\
Xvfb :99 -screen 0 1024x768x24 > /dev/null 2>&1 &\n\
echo "✅ Virtual display started"\n\
\n\
# Set environment variables for Railway deployment\n\
export WHATSAPP_SERVICE_URL="http://localhost:3005"  # Unified service main port\n\
export BACKEND_URL="http://localhost:$PORT"\n\
export BACKEND_PORT="$PORT"\n\
\n\
# Note: Unified service runs on ports 3005 (salon_a), 3006 (salon_b), 3007 (salon_c)\n\
\n\
# Start UNIFIED WhatsApp Web service in background (Railway-optimized)\n\
echo "📱 Starting Unified Multi-Salon WhatsApp Web service for Railway deployment..."\n\
node whatsapp-service-unified.js & \n\
WHATSAPP_PID=$!\n\
echo "✅ Unified WhatsApp Web service started with PID: $WHATSAPP_PID (ports 3005, 3006, 3007)"\n\
\n\
# Wait for WhatsApp services to initialize\n\
echo "⏰ Waiting for WhatsApp services to initialize..."\n\
sleep 15\n\
\n\
# Start FastAPI application on Railway PORT\n\
echo "🚀 Starting FastAPI backend on port $PORT..."\n\
echo "🔗 Service URLs:"\n\
echo "  📱 Production WhatsApp: http://localhost:3000"\n\
echo "  🏢 Main App: https://your-app.railway.app"\n\
echo "  📋 Health Check: https://your-app.railway.app/health"\n\
echo "  🎯 QR Codes: https://your-app.railway.app/qr"\n\
python3 -m uvicorn app.main:app --host 0.0.0.0 --port $PORT\n\
' > /app/start-railway.sh && chmod +x /app/start-railway.sh

# Health check endpoint for Railway - more lenient for startup
HEALTHCHECK --interval=30s --timeout=15s --start-period=120s --retries=5 \
    CMD curl -f http://localhost:$PORT/health || curl -f http://localhost:$PORT/ || exit 1

# Expose the port (Railway will set the PORT environment variable)
EXPOSE $PORT

# Use the Railway startup script
CMD ["/app/start-railway.sh"] 