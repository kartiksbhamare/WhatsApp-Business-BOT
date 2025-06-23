#!/bin/bash

echo "🚀 Starting Smart WhatsApp Booking Bot - Production Mode"

# Set up virtual display for headless Chrome
echo "🖥️ Starting virtual display..."
export DISPLAY=:99
Xvfb :99 -screen 0 1024x768x24 > /dev/null 2>&1 &
echo "✅ Virtual display started"

# Install dependencies if needed
echo "📦 Installing Node.js dependencies..."
npm install

echo "📦 Installing Python dependencies..."
pip3 install -r requirements.txt

# Set Chrome/Puppeteer environment variables for Railway
export CHROME_BIN=/usr/bin/google-chrome
export PUPPETEER_SKIP_CHROMIUM_DOWNLOAD=true
export PUPPETEER_EXECUTABLE_PATH=/usr/bin/google-chrome

# Start Node.js WhatsApp service in background
echo "📱 Starting WhatsApp Web service..."
node whatsapp-service-unified.js &

# Wait a moment for WhatsApp service to initialize
sleep 10

# Start Python FastAPI backend
echo "🐍 Starting FastAPI backend..."
python3 -m uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080} 