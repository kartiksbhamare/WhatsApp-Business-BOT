#!/bin/bash

# Railway WhatsApp Booking Bot Startup Script
# Environment-aware with retry logic and session management

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Set defaults for Railway environment
export BACKEND_URL=${BACKEND_URL:-"http://localhost:8000"}
export WHATSAPP_SERVICE_URL=${WHATSAPP_SERVICE_URL:-"http://localhost:3000"}
export BACKEND_PORT=${BACKEND_PORT:-8000}
export WHATSAPP_PORT=${WHATSAPP_PORT:-3000}
export SALON_NAME=${SALON_NAME:-"Beauty Salon"}
export RAILWAY_ENVIRONMENT=true

echo "🚂 Starting WhatsApp Bot on Railway"
echo "=================================================="
echo "🏢 Salon: $SALON_NAME"
echo "🔗 Backend URL: $BACKEND_URL"
echo "📱 WhatsApp URL: $WHATSAPP_SERVICE_URL"
echo "=================================================="

# Clean up any existing Chrome processes
cleanup_chrome() {
    echo "🧹 Cleaning up Chrome processes..."
    pkill -f "chrome" 2>/dev/null || true
    pkill -f "chromium" 2>/dev/null || true
    rm -rf /tmp/.X* /tmp/chrome-* 2>/dev/null || true
    sleep 2
}

# Initialize WhatsApp client with retry logic
initialize_whatsapp() {
    local attempt=$1
    local max_attempts=5
    
    echo "🔄 [$SALON_NAME] Initializing WhatsApp client (attempt $attempt/$max_attempts)..."
    
    # Clean up before each attempt
    cleanup_chrome
    rm -rf .wwebjs_auth/session* 2>/dev/null || true
    
    # Start the WhatsApp service
    timeout 120s node whatsapp-simple.js &
    local whatsapp_pid=$!
    
    # Wait for initialization with timeout
    local wait_time=0
    local max_wait=90
    
    while [ $wait_time -lt $max_wait ]; do
        if ps -p $whatsapp_pid > /dev/null 2>&1; then
            sleep 5
            wait_time=$((wait_time + 5))
            
            # Check if service is responding
            if curl -s -f http://localhost:$WHATSAPP_PORT/health > /dev/null 2>&1; then
                echo "✅ [$SALON_NAME] WhatsApp service initialized successfully!"
                return 0
            fi
        else
            echo "❌ [$SALON_NAME] WhatsApp process died during initialization"
            break
        fi
    done
    
    echo "⏰ [$SALON_NAME] Initialization timeout or failure"
    kill $whatsapp_pid 2>/dev/null || true
    return 1
}

# Main startup logic with retry
attempt=1
max_attempts=5

while [ $attempt -le $max_attempts ]; do
    echo ""
    echo "🚀 Starting attempt $attempt/$max_attempts..."
    
    if initialize_whatsapp $attempt; then
        echo "🎉 [$SALON_NAME] WhatsApp Bot started successfully!"
        echo ""
        echo "✅ Service URLs:"
        echo "📱 QR Code: $WHATSAPP_SERVICE_URL/qr"
        echo "🔍 Health: $WHATSAPP_SERVICE_URL/health"
        echo ""
        
        # Keep the service running
        while true; do
            sleep 30
            # Health check
            if ! curl -s -f http://localhost:$WHATSAPP_PORT/health > /dev/null 2>&1; then
                echo "⚠️ [$SALON_NAME] Health check failed, service may have crashed"
                break
            fi
        done
        
        # If we get here, the service crashed, try to restart
        echo "🔄 [$SALON_NAME] Service crashed, attempting restart..."
        cleanup_chrome
    else
        echo "❌ [$SALON_NAME] Attempt $attempt failed"
    fi
    
    if [ $attempt -lt $max_attempts ]; then
        local delay=$((attempt * 10))
        echo "⏰ [$SALON_NAME] Waiting ${delay}s before retry..."
        sleep $delay
    fi
    
    attempt=$((attempt + 1))
done

echo "💥 [$SALON_NAME] Failed to start after $max_attempts attempts"
echo "🔧 Check Railway logs for Chrome/Puppeteer errors"
exit 1 