#!/bin/bash

echo "🐳 Starting WhatsApp Booking Bot in Docker"
echo "=========================================="

# Check if firebase-key.json exists
if [ ! -f "firebase-key.json" ]; then
    echo "❌ firebase-key.json not found!"
    echo ""
    echo "📋 Please create Firebase service account key:"
    echo "1. Go to: https://console.firebase.google.com/project/appointment-booking-4c50f/settings/serviceaccounts/adminsdk"
    echo "2. Click 'Generate new private key'"
    echo "3. Save as 'firebase-key.json' in this directory"
    echo ""
    echo "Then run this script again: ./run_docker.sh"
    exit 1
fi

echo "✅ firebase-key.json found!"
echo ""

# Stop any existing container
echo "🛑 Stopping existing containers..."
docker-compose down 2>/dev/null || true

# Build and start the container
echo "🔨 Building Docker image..."
docker-compose build

echo "🚀 Starting WhatsApp bot container..."
docker-compose up -d

echo ""
echo "🎉 Container started successfully!"
echo ""
echo "📱 Services:"
echo "  - WhatsApp QR Code: http://localhost:3000/qr"
echo "  - Backend API: http://localhost:8000"
echo "  - Health Check: http://localhost:8000/health"
echo ""
echo "📋 Commands:"
echo "  - View logs: docker-compose logs -f"
echo "  - Stop: docker-compose down"
echo "  - Restart: docker-compose restart"
echo ""
echo "🎯 Next Steps:"
echo "1. Open http://localhost:3000/qr in your browser"
echo "2. Scan QR code with WhatsApp on your phone"
echo "3. Send 'hi' to test the bot" 