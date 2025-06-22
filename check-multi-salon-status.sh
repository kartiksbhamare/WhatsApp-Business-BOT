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
                    # Extract status
                    status=$(echo "$response" | grep -o '"status":"[^"]*"' | cut -d'"' -f4)
                    echo "  💡 Status: $status"
                    
                    # Check for connection status (for WhatsApp services)
                    connection_info=$(echo "$response" | grep -o '"connection_status":{[^}]*}')
                    if [[ -n "$connection_info" ]]; then
                        is_connected=$(echo "$connection_info" | grep -o '"is_connected":[^,]*' | cut -d':' -f2)
                        phone_number=$(echo "$connection_info" | grep -o '"phone_number":"[^"]*"' | cut -d'"' -f4)
                        connection_count=$(echo "$connection_info" | grep -o '"connection_count":[^,]*' | cut -d':' -f2)
                        
                        if [[ "$is_connected" == "true" && "$phone_number" != "null" ]]; then
                            echo "  📱 WhatsApp: ✅ Connected ($phone_number)"
                            echo "  🔢 Total connections: $connection_count"
                        else
                            echo "  📱 WhatsApp: ❌ Not connected (connections: $connection_count)"
                        fi
                    fi
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

# Check connection status specifically
check_connection_status() {
    local name=$1
    local port=$2
    local salon_id=$3
    
    echo "📱 Checking WhatsApp connection for $name..."
    
    local connection_url="http://localhost:$port/connection-status"
    if curl -s "$connection_url" >/dev/null 2>&1; then
        response=$(curl -s "$connection_url" 2>/dev/null)
        if [[ $? -eq 0 ]]; then
            is_connected=$(echo "$response" | grep -o '"is_connected":[^,]*' | cut -d':' -f2)
            phone_number=$(echo "$response" | grep -o '"phone_number":"[^"]*"' | cut -d'"' -f4)
            connected_at=$(echo "$response" | grep -o '"connected_at":"[^"]*"' | cut -d'"' -f4)
            qr_needed=$(echo "$response" | grep -o '"qr_needed":[^,]*' | cut -d':' -f2)
            
            if [[ "$is_connected" == "true" && "$phone_number" != "null" ]]; then
                echo "  ✅ Connected: $phone_number"
                echo "  🕒 Since: $connected_at"
                echo "  🎯 Action: Ready to receive messages"
            elif [[ "$qr_needed" == "true" ]]; then
                echo "  ❌ Not connected"
                echo "  🎯 Action: Scan QR code at http://localhost:$port/qr"
            else
                echo "  ⏳ Initializing connection..."
                echo "  🎯 Action: Wait for QR code generation"
            fi
        fi
    else
        echo "  ❌ Cannot check connection status"
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

echo "🔗 WhatsApp Connection Details:"
echo ""
check_connection_status "Salon A (Downtown Beauty)" 3005 "salon_a"
check_connection_status "Salon B (Uptown Hair)" 3006 "salon_b"
check_connection_status "Salon C (Luxury Spa)" 3007 "salon_c"

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