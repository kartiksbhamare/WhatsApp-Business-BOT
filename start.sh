#!/bin/bash
set -e

echo "🚀 Starting Smart WhatsApp Booking Bot - Railway Production"

# Set environment variables
export DISPLAY=:99
export CHROME_BIN=/usr/bin/google-chrome
export PUPPETEER_SKIP_CHROMIUM_DOWNLOAD=true
export PUPPETEER_EXECUTABLE_PATH=/usr/bin/google-chrome

# Check if Chrome is available
echo "🔍 Checking Chrome installation..."
if command -v google-chrome &> /dev/null; then
    echo "✅ Chrome found: $(google-chrome --version)"
else
    echo "❌ Chrome not found!"
    exit 1
fi

# Start virtual display
echo "🖥️ Starting virtual display..."
Xvfb :99 -screen 0 1024x768x24 > /dev/null 2>&1 &
sleep 2

# Check Node.js and npm versions
echo "🔍 Checking Node.js..."
node --version
npm --version

# Install dependencies if needed
echo "📦 Installing Node.js dependencies..."
npm install --production

# Run a quick test to see if the WhatsApp service can start
echo "🧪 Running WhatsApp service test..."
timeout 30 node test-whatsapp-simple.js || echo "⚠️ Test completed or timed out"

# Start WhatsApp service in background with detailed logging
echo "📱 Starting WhatsApp Web service..."
echo "📋 Command: node whatsapp-service-unified.js"
node whatsapp-service-unified.js > whatsapp.log 2>&1 &
WHATSAPP_PID=$!
echo "✅ WhatsApp service started with PID: $WHATSAPP_PID"

# Wait for WhatsApp service to initialize
echo "⏰ Waiting for WhatsApp service to initialize..."
sleep 20

# Check if WhatsApp service is running
if ps -p $WHATSAPP_PID > /dev/null; then
    echo "✅ WhatsApp service is running"
    echo "📋 Checking if ports are listening..."
    netstat -tulpn | grep :300 || echo "No ports 3005-3007 found"
else
    echo "❌ WhatsApp service failed to start"
    echo "📋 WhatsApp logs:"
    cat whatsapp.log || echo "No logs available"
    echo "📋 Attempting to start WhatsApp service directly..."
    node whatsapp-service-unified.js &
    sleep 10
fi

# Show recent WhatsApp logs
echo "📋 Recent WhatsApp logs:"
tail -20 whatsapp.log || echo "No recent logs"

# Start FastAPI backend (this keeps the container alive)
echo "🐍 Starting FastAPI backend on port ${PORT:-8080}..."
exec python3 -m uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080} 