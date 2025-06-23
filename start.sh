#!/bin/bash
set -e

echo "🚀 Starting Smart WhatsApp Booking Bot - Railway Production"

# Set environment variables
export DISPLAY=:99
export CHROME_BIN=/usr/bin/google-chrome
export PUPPETEER_SKIP_CHROMIUM_DOWNLOAD=true
export PUPPETEER_EXECUTABLE_PATH=/usr/bin/google-chrome

# Clean up any existing Chrome processes and temp files
echo "🧹 Cleaning up any existing Chrome processes and temp files..."
pkill -f chrome || echo "No existing Chrome processes found"
pkill -f chromium || echo "No existing Chromium processes found"
rm -rf /tmp/chrome-user-data* || echo "No temp Chrome data to clean"
rm -rf /tmp/.org.chromium.* || echo "No Chromium temp files to clean"
sleep 3

# Check if Chrome is available
echo "🔍 Checking Chrome installation..."
if command -v google-chrome &> /dev/null; then
    echo "✅ Chrome found: $(google-chrome --version)"
else
    echo "❌ Chrome not found!"
    exit 1
fi

# Start virtual display with larger screen
echo "🖥️ Starting virtual display..."
Xvfb :99 -screen 0 1920x1080x24 -ac -nolisten tcp -dpi 96 > /dev/null 2>&1 &
sleep 5

# Test Chrome with virtual display multiple times for stability
echo "🧪 Testing Chrome stability with virtual display..."
for i in {1..3}; do
    echo "🔄 Chrome test attempt $i/3..."
    timeout 15 google-chrome --headless --no-sandbox --disable-gpu --virtual-time-budget=2000 --run-all-compositor-stages-before-draw --dump-dom about:blank > /dev/null 2>&1 && echo "✅ Chrome test $i successful" || echo "⚠️ Chrome test $i failed but continuing"
    sleep 2
done

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

# Wait longer for WhatsApp service to initialize (Chrome needs more time for stability)
echo "⏰ Waiting for WhatsApp service to initialize (60 seconds)..."
sleep 60

# Check if WhatsApp service is running
if ps -p $WHATSAPP_PID > /dev/null; then
    echo "✅ WhatsApp service is running"
    echo "📋 Checking if ports are listening..."
    netstat -tulpn | grep :300 || echo "Ports may still be starting up..."
else
    echo "❌ WhatsApp service failed to start"
    echo "📋 WhatsApp logs:"
    cat whatsapp.log || echo "No logs available"
    echo "📋 Attempting to start WhatsApp service directly..."
    node whatsapp-service-unified.js &
    sleep 15
fi

# Show recent WhatsApp logs
echo "📋 Recent WhatsApp logs:"
tail -30 whatsapp.log || echo "No recent logs"

# Start FastAPI backend (this keeps the container alive)
echo "🐍 Starting FastAPI backend on port ${PORT:-8080}..."
exec python3 -m uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080} 