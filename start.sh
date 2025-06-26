#!/bin/bash

echo "🚀 Starting Simple WhatsApp Booking Bot"
echo "========================================"

# Kill any existing processes
echo "🧹 Cleaning up existing processes..."
pkill -f "uvicorn" 2>/dev/null
pkill -f "node.*whatsapp" 2>/dev/null
pkill -f "chrome" 2>/dev/null

# Wait for cleanup
sleep 2

# Set environment variables for single salon
export SALON_NAME="Beauty Salon"
export PORT=3000

echo "📋 Configuration:"
echo "  Salon Name: $SALON_NAME"
echo "  WhatsApp Port: $PORT"
echo "  Backend Port: 8000"

# Start backend
echo ""
echo "🐍 Starting Python Backend..."
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

# Wait for backend to start
sleep 3

# Start WhatsApp service
echo ""
echo "📱 Starting WhatsApp Service..."
node whatsapp-simple.js &
WHATSAPP_PID=$!

# Wait for services to start
sleep 5

echo ""
echo "✅ Services Started!"
echo "📱 WhatsApp QR Code: http://localhost:3000/qr"
echo "🐍 Backend API: http://localhost:8000"
echo "📋 Health Check: http://localhost:8000/health"

echo ""
echo "🎯 Next Steps:"
echo "1. Open http://localhost:3000/qr in your browser"
echo "2. Scan the QR code with WhatsApp on your phone"
echo "3. Send 'hi' to your WhatsApp number to test the bot"

# Wait for user to stop
echo ""
echo "Press Ctrl+C to stop all services..."

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "🛑 Stopping services..."
    kill $BACKEND_PID 2>/dev/null
    kill $WHATSAPP_PID 2>/dev/null
    pkill -f "uvicorn" 2>/dev/null
    pkill -f "node.*whatsapp" 2>/dev/null
    echo "👋 All services stopped. Goodbye!"
    exit 0
}

# Set trap to cleanup on Ctrl+C
trap cleanup INT

# Wait indefinitely
wait 