#!/bin/bash

# Multi-Salon Status Checker
echo "🔍 Multi-Salon WhatsApp Booking Bot Status Check"
echo "================================================="

# Function to check service health
check_service() {
    local name=$1
    local url=$2
    local port=$3
    
    echo "🔍 Checking $name..."
    
    # Check if port is listening
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo "  📡 Port $port: ✅ Listening"
        
        # Try HTTP health check
        if curl -s "$url" >/dev/null 2>&1; then
            echo "  🌐 HTTP: ✅ Responding"
            
            # Get service-specific info
            if [[ "$url" == *"/health"* ]]; then
                response=$(curl -s "$url" 2>/dev/null)
                if [[ $? -eq 0 ]]; then
                    echo "  💡 Status: $(echo "$response" | grep -o '"status":"[^"]*"' | cut -d'"' -f4)"
                fi
            fi
        else
            echo "  🌐 HTTP: ❌ Not responding"
        fi
    else
        echo "  📡 Port $port: ❌ Not listening"
        echo "  🌐 HTTP: ❌ Service offline"
    fi
    echo ""
}

# Check all services
echo "📊 Service Health Check:"
echo ""

check_service "Backend API" "http://localhost:8000/health" 8000
check_service "Salon A WhatsApp" "http://localhost:3005/health" 3005  
check_service "Salon B WhatsApp" "http://localhost:3006/health" 3006
check_service "Salon C WhatsApp" "http://localhost:3007/health" 3007

echo "🎯 Quick Links:"
echo "📊 Backend Health: http://localhost:8000/health"
echo "📱 Salon A QR: http://localhost:3005/qr"
echo "📱 Salon B QR: http://localhost:3006/qr"  
echo "📱 Salon C QR: http://localhost:3007/qr"
echo ""
echo "📋 API Endpoints:"
echo "🏢 Salons: http://localhost:8000/api/salons"
echo "🛍️  Services: http://localhost:8000/api/services/{salon_id}"
echo "✂️  Barbers: http://localhost:8000/api/barbers/{salon_id}" 