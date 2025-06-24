#!/bin/bash

echo "🚀 Starting Simple WhatsApp Booking Bot"
echo "========================================"

# Kill any existing processes and clean up
echo "🧹 Cleaning up..."
pkill -f "uvicorn" 2>/dev/null
pkill -f "node.*whatsapp" 2>/dev/null
pkill -f "chrome" 2>/dev/null
pkill -f "Google Chrome" 2>/dev/null

# Clean up session files and temp data
rm -rf .wwebjs_auth connection_status*.json *.png /tmp/whatsapp-chrome-data 2>/dev/null

sleep 3

# Set environment variables
export SALON_NAME="Beauty Salon"
export PORT=3000

echo "📋 Configuration:"
echo "  Salon Name: $SALON_NAME"
echo "  WhatsApp Port: $PORT"
echo "  Backend Port: 8000"

# Start backend first
echo ""
echo "🐍 Starting Python Backend..."
python3 -m uvicorn app.main_simple:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

# Wait for backend to start
sleep 5

echo "✅ Backend started on port 8000"

# Start WhatsApp service with retry logic
echo ""
echo "📱 Starting WhatsApp Service..."

start_whatsapp() {
    node whatsapp-service-unified.js &
    WHATSAPP_PID=$!
    
    # Wait and check if it's still running
    sleep 10
    
    if ps -p $WHATSAPP_PID > /dev/null 2>&1; then
        echo "✅ WhatsApp service started successfully on port 3000"
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
    echo "   3. Manually restart with: node whatsapp-service-unified.js"
fi

echo ""
echo "🎯 Access Points:"
echo "📱 WhatsApp QR Code: http://localhost:3000/qr"
echo "🐍 Backend API: http://localhost:8000"
echo "📋 Health Check: http://localhost:8000/health"

echo ""
echo "🎯 Next Steps:"
echo "1. Open http://localhost:3000/qr in your browser"
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