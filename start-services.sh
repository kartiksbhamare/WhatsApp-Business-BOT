#!/bin/bash

# Smart WhatsApp Booking Bot - Service Startup Script

echo "🚀 Starting Smart WhatsApp Booking Bot Services"
echo "================================================"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check if Node.js is installed
if ! command_exists node; then
    echo "❌ Node.js is not installed. Please install Node.js first."
    exit 1
fi

# Check if Python is installed
if ! command_exists python3; then
    echo "❌ Python 3 is not installed. Please install Python 3 first."
    exit 1
fi

# Install Node.js dependencies if needed
if [ ! -d "node_modules" ]; then
    echo -e "${YELLOW}📦 Installing Node.js dependencies...${NC}"
    npm install
fi

# Install Python dependencies if needed
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}🐍 Creating Python virtual environment...${NC}"
    python3 -m venv venv
fi

echo -e "${YELLOW}📋 Activating Python virtual environment...${NC}"
source venv/bin/activate

echo -e "${YELLOW}📦 Installing Python dependencies...${NC}"
pip install -r requirements.txt

# Start WhatsApp Web service in background
echo -e "${BLUE}📱 Starting WhatsApp Web service...${NC}"
nohup node whatsapp-service.js > whatsapp.log 2>&1 &
WHATSAPP_PID=$!
echo "WhatsApp Web service started with PID: $WHATSAPP_PID"

# Wait a moment for WhatsApp service to start
sleep 3

# Start Python FastAPI application
echo -e "${GREEN}🚀 Starting FastAPI application...${NC}"
echo "================================================"
echo "📱 Scan the QR code that appears in whatsapp.log with your WhatsApp"
echo "🌐 FastAPI will be available at: http://localhost:8000"
echo "📊 API Documentation: http://localhost:8000/docs"
echo "================================================"

# Run the Python application
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Cleanup function
cleanup() {
    echo "🛑 Shutting down services..."
    kill $WHATSAPP_PID 2>/dev/null
    echo "✅ Services stopped"
    exit 0
}

# Trap SIGINT (Ctrl+C) and call cleanup
trap cleanup SIGINT

# Keep the script running
wait 