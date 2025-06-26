#!/bin/bash

# Smart WhatsApp Booking Bot - Startup Script
# Environment-aware startup with configurable URLs

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Set defaults if not provided
export BACKEND_URL=${BACKEND_URL:-"http://localhost:8000"}
export WHATSAPP_SERVICE_URL=${WHATSAPP_SERVICE_URL:-"http://localhost:3000"}
export BACKEND_PORT=${BACKEND_PORT:-8000}
export WHATSAPP_PORT=${WHATSAPP_PORT:-3000}
export SALON_NAME=${SALON_NAME:-"Beauty Salon"}

echo "🚀 Starting Smart WhatsApp Booking Bot"
echo "=================================================="
echo "🏢 Salon: $SALON_NAME"
echo "🔗 Backend URL: $BACKEND_URL"
echo "📱 WhatsApp URL: $WHATSAPP_SERVICE_URL"
echo "=================================================="

# Start backend
echo "🐍 Starting Python Backend..."
python -m uvicorn app.main_simple:app --host 0.0.0.0 --port $BACKEND_PORT &
BACKEND_PID=$!

# Wait for backend to start
sleep 5

# Start WhatsApp service
echo "📱 Starting WhatsApp Service..."
node whatsapp-simple.js &
WHATSAPP_PID=$!

# Wait for services to initialize
sleep 3

echo ""
echo "✅ Services Started Successfully!"
echo "=================================================="
echo "📱 WhatsApp QR Code: $WHATSAPP_SERVICE_URL/qr"
echo "🐍 Backend API: $BACKEND_URL"
echo "📋 Health Check: $BACKEND_URL/health"
echo "=================================================="
echo ""
echo "1. Open $WHATSAPP_SERVICE_URL/qr in your browser"
echo "2. Scan the QR code with WhatsApp"
echo "3. Send 'hi' to test the bot"
echo ""
echo "Press Ctrl+C to stop all services"

# Wait for user interrupt
wait $BACKEND_PID $WHATSAPP_PID 