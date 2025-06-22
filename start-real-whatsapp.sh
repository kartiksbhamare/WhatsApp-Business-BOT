#!/bin/bash

echo "🚀 Starting REAL WhatsApp Web Service for Multi-Salon System"
echo ""
echo "⚠️  IMPORTANT: This will start actual WhatsApp Web.js clients"
echo "📱 You'll need to scan QR codes with your phone to connect"
echo ""

# Check if Node.js dependencies are installed
if [ ! -d "node_modules" ]; then
    echo "📦 Installing Node.js dependencies..."
    npm install
fi

# Kill any existing WhatsApp services
echo "🛑 Stopping any existing WhatsApp services..."
pkill -f "whatsapp-service"
pkill -f "mock-whatsapp"

# Start the real WhatsApp service
echo "🚀 Starting Real WhatsApp Web Service..."
echo "📱 This will generate actual QR codes for WhatsApp Web connection"
echo ""

# Export environment for real WhatsApp service
export NODE_ENV=production
export WHATSAPP_MODE=real

# Start the service
node whatsapp-service-real.js &
WHATSAPP_PID=$!

echo "✅ Real WhatsApp Web Service started with PID: $WHATSAPP_PID"
echo ""
echo "🔗 Access the service at: http://localhost:3000"
echo "📋 Each salon will have its own QR code to scan"
echo ""
echo "🏢 Available Salons:"
echo "   • Downtown Beauty Salon: http://localhost:3000/qr/salon_a"
echo "   • Uptown Hair Studio: http://localhost:3000/qr/salon_b" 
echo "   • Luxury Spa & Salon: http://localhost:3000/qr/salon_c"
echo ""
echo "📱 How to connect:"
echo "   1. Open one of the salon URLs above"
echo "   2. Scan the QR code with WhatsApp (Settings → Linked Devices → Link a Device)"
echo "   3. Send 'hi' to start booking for that salon"
echo ""
echo "🛑 Press Ctrl+C to stop the service"

# Wait for the process
wait $WHATSAPP_PID 