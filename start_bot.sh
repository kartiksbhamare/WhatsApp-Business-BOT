#!/bin/bash

echo "🚀 Starting WhatsApp Booking Bot"
echo "================================"

# Kill any existing processes
pkill -f "uvicorn.*main_simple" 2>/dev/null
pkill -f "node.*whatsapp-simple" 2>/dev/null
sleep 2

# Clean up old files
rm -f *.png

echo "🐍 Starting Backend..."
python3 -m uvicorn app.main_simple:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

echo "📱 Starting WhatsApp Service..."
SALON_NAME="Beauty Salon" PORT=3000 node whatsapp-simple.js &
WHATSAPP_PID=$!

sleep 3

echo ""
echo "✅ Services Started!"
echo "📱 WhatsApp QR Code: http://localhost:3000/qr"
echo "🐍 Backend API: http://localhost:8000"
echo "📋 Health Check: http://localhost:8000/health"
echo ""
echo "🎯 Next Steps:"
echo "1. Open http://localhost:3000/qr in your browser"
echo "2. Scan QR code with WhatsApp on your phone"
echo "3. Send 'hi' to test the bot"
echo ""
echo "Press Ctrl+C to stop..."

# Cleanup function
cleanup() {
    echo ""
    echo "🛑 Stopping services..."
    kill $BACKEND_PID $WHATSAPP_PID 2>/dev/null
    pkill -f "uvicorn.*main_simple" 2>/dev/null
    pkill -f "node.*whatsapp-simple" 2>/dev/null
    echo "👋 Stopped!"
    exit 0
}

trap cleanup INT
wait 