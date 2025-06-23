#!/bin/bash

echo "🚀 Starting Smart WhatsApp Booking Bot - Production Mode"

# Install dependencies if needed
echo "📦 Installing Node.js dependencies..."
npm install

echo "📦 Installing Python dependencies..."
pip install -r requirements.txt

# Start Node.js WhatsApp service in background
echo "📱 Starting WhatsApp Web service..."
node whatsapp-service-unified.js &

# Wait a moment for WhatsApp service to initialize
sleep 5

# Start Python FastAPI backend
echo "🐍 Starting FastAPI backend..."
python -m uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080} 