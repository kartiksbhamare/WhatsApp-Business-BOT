#!/bin/bash

echo "🚀 Starting WhatsApp Booking Bot for Railway"
echo "============================================="

# Set Railway-specific environment variables
export RAILWAY_ENVIRONMENT=true
export DOCKER_ENV=true
export NODE_ENV=production
export SALON_NAME="Beauty Salon"
export PORT=3000

# Clean up any existing Chrome processes
pkill -f "chrome" 2>/dev/null || true
pkill -f "chromium" 2>/dev/null || true

# Clean up old session files if they exist and are corrupted
if [ -d "/app/.wwebjs_auth" ]; then
    echo "🧹 Checking for corrupted session files..."
    # Remove any lock files that might prevent startup
    find /app/.wwebjs_auth -name "*.lock" -delete 2>/dev/null || true
fi

echo "📋 Railway Configuration:"
echo "  Environment: Railway Cloud"
echo "  Salon Name: $SALON_NAME"
echo "  WhatsApp Port: $PORT"
echo "  Backend Port: 8000"
echo "  Chrome Path: /usr/bin/google-chrome-stable"

# Start backend
echo ""
echo "🐍 Starting Python Backend..."
python3 -m uvicorn app.main_simple:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

# Wait for backend to start
sleep 5

# Start WhatsApp service with retry logic
echo ""
echo "📱 Starting WhatsApp Service with Railway optimizations..."

# Function to start WhatsApp with retries
start_whatsapp() {
    local attempt=1
    local max_attempts=3
    
    while [ $attempt -le $max_attempts ]; do
        echo "🔄 Attempt $attempt of $max_attempts..."
        
        # Start WhatsApp service
        timeout 120 node whatsapp-simple.js &
        WHATSAPP_PID=$!
        
        # Wait and check if it's still running
        sleep 30
        
        if kill -0 $WHATSAPP_PID 2>/dev/null; then
            echo "✅ WhatsApp service started successfully!"
            return 0
        else
            echo "❌ WhatsApp service failed to start (attempt $attempt)"
            wait $WHATSAPP_PID 2>/dev/null
            attempt=$((attempt + 1))
            
            if [ $attempt -le $max_attempts ]; then
                echo "⏰ Waiting 10 seconds before retry..."
                sleep 10
                
                # Clean up any Chrome processes
                pkill -f "chrome" 2>/dev/null || true
                pkill -f "chromium" 2>/dev/null || true
            fi
        fi
    done
    
    echo "❌ Failed to start WhatsApp service after $max_attempts attempts"
    return 1
}

# Start WhatsApp with retries
if start_whatsapp; then
    echo ""
    echo "✅ All Services Started Successfully!"
    echo "📱 WhatsApp QR Code: https://your-app.railway.app/qr"
    echo "🐍 Backend API: https://your-app.railway.app"
    echo "📋 Health Check: https://your-app.railway.app/health"
    
    # Wait for WhatsApp service
    wait $WHATSAPP_PID
else
    echo "❌ Failed to start services"
    kill $BACKEND_PID 2>/dev/null
    exit 1
fi 