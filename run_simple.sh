#!/bin/bash

# Smart WhatsApp Booking Bot - Complete Setup & Run Script
# Environment-aware with configurable URLs

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

# Kill any existing processes and clean up
echo "🧹 Cleaning up..."
pkill -f "uvicorn" 2>/dev/null
pkill -f "node.*whatsapp" 2>/dev/null
pkill -f "chrome" 2>/dev/null
pkill -f "Google Chrome" 2>/dev/null

# Clean up session files and temp data
rm -rf .wwebjs_auth connection_status*.json *.png /tmp/whatsapp-chrome-data 2>/dev/null

sleep 3

echo "📋 Configuration:"
echo "  Salon Name: $SALON_NAME"
echo "  WhatsApp Port: $WHATSAPP_PORT"
echo "  Backend Port: $BACKEND_PORT"

# Start backend first
echo ""
echo "🐍 Starting Python Backend..."
python3 -m uvicorn app.main_simple:app --host 0.0.0.0 --port $BACKEND_PORT &
BACKEND_PID=$!

# Wait for backend to start
sleep 5

echo "✅ Backend started on port $BACKEND_PORT"

# Start WhatsApp service with retry logic
echo ""
echo "📱 Starting WhatsApp Service..."

start_whatsapp() {
    PORT=$WHATSAPP_PORT node whatsapp-simple.js &
    WHATSAPP_PID=$!
    
    # Wait and check if it's still running
    sleep 10
    
    if ps -p $WHATSAPP_PID > /dev/null 2>&1; then
        echo "✅ WhatsApp service started successfully on port $WHATSAPP_PORT"
        return 0
    else
        echo "❌ WhatsApp service failed to start, retrying..."
        return 1
    fi
}

# Try to start WhatsApp service up to 3 times
RETRY_COUNT=0
MAX_RETRIES=3

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    echo "🔄 WhatsApp start attempt $((RETRY_COUNT + 1))/$MAX_RETRIES"
    
    if start_whatsapp; then
        break
    fi
    
    RETRY_COUNT=$((RETRY_COUNT + 1))
    
    if [ $RETRY_COUNT -lt $MAX_RETRIES ]; then
        echo "⏰ Waiting 5 seconds before retry..."
        sleep 5
        
        # Clean up before retry
        pkill -f "node.*whatsapp" 2>/dev/null
        pkill -f "chrome" 2>/dev/null
        rm -rf .wwebjs_auth /tmp/whatsapp-chrome-data 2>/dev/null
        sleep 2
    fi
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo "❌ Failed to start WhatsApp service after $MAX_RETRIES attempts"
    echo "🔧 You can try:"
    echo "   1. Check if Chrome is properly installed"
    echo "   2. Run: which 'Google Chrome' or ls '/Applications/Google Chrome.app'"
    echo "   3. Manually restart with: PORT=$WHATSAPP_PORT node whatsapp-simple.js"
fi

echo ""
echo "✅ All Services Started Successfully!"
echo "=================================================="
echo "📱 WhatsApp QR Code: $WHATSAPP_SERVICE_URL/qr"
echo "🐍 Backend API: $BACKEND_URL"
echo "📋 Health Check: $BACKEND_URL/health"
echo "=================================================="

echo ""
echo "🎯 Next Steps:"
echo "1. Open $WHATSAPP_SERVICE_URL/qr in your browser"
echo "2. Scan the QR code with WhatsApp on your phone"
echo "3. Send 'hi' to your WhatsApp number to test the bot"

echo ""
echo "Press Ctrl+C to stop all services..."

# Cleanup function
cleanup() {
    echo ""
    echo "🛑 Stopping services..."
    kill $BACKEND_PID 2>/dev/null
    kill $WHATSAPP_PID 2>/dev/null
    pkill -f "uvicorn" 2>/dev/null
    pkill -f "node.*whatsapp" 2>/dev/null
    pkill -f "chrome" 2>/dev/null
    echo "👋 All services stopped. Goodbye!"
    exit 0
}

# Set trap for cleanup
trap cleanup INT

# Wait indefinitely
wait 