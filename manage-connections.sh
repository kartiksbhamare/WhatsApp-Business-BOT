#!/bin/bash

# Multi-Salon Connection Management Script
echo "🔧 Multi-Salon WhatsApp Connection Manager"
echo "==========================================="

# Function to show connection status
show_status() {
    echo "📋 Current Connection Status:"
    echo ""
    
    for salon in salon_a salon_b salon_c; do
        case $salon in
            salon_a) name="Downtown Beauty Salon"; port=3005 ;;
            salon_b) name="Uptown Hair Studio"; port=3006 ;;
            salon_c) name="Luxury Spa & Salon"; port=3007 ;;
        esac
        
        status_file="connection_status_${salon}.json"
        echo "🏢 $name ($salon):"
        
        if [ -f "$status_file" ]; then
            is_connected=$(grep -o '"is_connected":[^,]*' "$status_file" | cut -d':' -f2)
            phone_number=$(grep -o '"phone_number":"[^"]*"' "$status_file" | cut -d'"' -f4)
            connected_at=$(grep -o '"connected_at":"[^"]*"' "$status_file" | cut -d'"' -f4)
            connection_count=$(grep -o '"connection_count":[^,]*' "$status_file" | cut -d':' -f2)
            
            if [[ "$is_connected" == "true" && "$phone_number" != "null" ]]; then
                echo "  ✅ Status: Connected"
                echo "  📱 Phone: $phone_number"
                echo "  🕒 Connected: $connected_at"
                echo "  🔢 Total connections: $connection_count"
                echo "  🎯 QR Code: Not needed (already connected)"
            else
                echo "  ❌ Status: Not connected"
                echo "  🔢 Previous connections: $connection_count"
                echo "  🎯 QR Code: http://localhost:$port/qr"
            fi
        else
            echo "  ⚪ Status: No connection history"
            echo "  🎯 QR Code: http://localhost:$port/qr"
        fi
        echo ""
    done
}

# Function to reset specific salon connection
reset_salon() {
    local salon=$1
    
    case $salon in
        salon_a|a|1) salon="salon_a"; name="Downtown Beauty Salon"; port=3005 ;;
        salon_b|b|2) salon="salon_b"; name="Uptown Hair Studio"; port=3006 ;;
        salon_c|c|3) salon="salon_c"; name="Luxury Spa & Salon"; port=3007 ;;
        *) echo "❌ Invalid salon ID. Use: salon_a, salon_b, salon_c (or a, b, c)"; return 1 ;;
    esac
    
    echo "🔄 Resetting connection for $name..."
    
    # Call the reset endpoint
    response=$(curl -s -X POST "http://localhost:$port/reset-connection" 2>/dev/null)
    
    if [[ $? -eq 0 ]]; then
        success=$(echo "$response" | grep -o '"success":[^,]*' | cut -d':' -f2)
        message=$(echo "$response" | grep -o '"message":"[^"]*"' | cut -d'"' -f4)
        
        if [[ "$success" == "true" ]]; then
            echo "✅ $message"
            echo "🎯 Next step: Restart the service and scan new QR code"
        else
            echo "❌ Reset failed: $message"
        fi
    else
        echo "❌ Cannot connect to $name service on port $port"
        echo "💡 Make sure the service is running"
    fi
}

# Function to reset all connections
reset_all() {
    echo "🔄 Resetting all salon connections..."
    echo ""
    
    for salon in salon_a salon_b salon_c; do
        reset_salon $salon
        echo ""
    done
    
    echo "⚠️  To complete the reset:"
    echo "1. Stop all services: ./stop-multi-salon-services.sh"
    echo "2. Start all services: ./start-multi-salon-services.sh"
    echo "3. Scan new QR codes for each salon"
}

# Function to show QR codes for unconnected salons
show_qr_links() {
    echo "📱 QR Code Links (for unconnected salons):"
    echo ""
    
    for salon in salon_a salon_b salon_c; do
        case $salon in
            salon_a) name="Downtown Beauty Salon"; port=3005 ;;
            salon_b) name="Uptown Hair Studio"; port=3006 ;;
            salon_c) name="Luxury Spa & Salon"; port=3007 ;;
        esac
        
        status_file="connection_status_${salon}.json"
        
        if [ -f "$status_file" ]; then
            is_connected=$(grep -o '"is_connected":[^,]*' "$status_file" | cut -d':' -f2)
            if [[ "$is_connected" != "true" ]]; then
                echo "❌ $name: http://localhost:$port/qr"
            else
                echo "✅ $name: Already connected"
            fi
        else
            echo "⚪ $name: http://localhost:$port/qr"
        fi
    done
}

# Main script logic
case "${1:-status}" in
    "status"|"s")
        show_status
        ;;
    "qr"|"q")
        show_qr_links
        ;;
    "reset")
        if [ -n "$2" ]; then
            reset_salon "$2"
        else
            echo "❌ Please specify salon: reset salon_a, reset salon_b, or reset salon_c"
            echo "💡 Or use: reset-all to reset all salons"
        fi
        ;;
    "reset-all"|"reset_all")
        reset_all
        ;;
    "help"|"h")
        echo "📖 Usage:"
        echo "  ./manage-connections.sh [command]"
        echo ""
        echo "🔧 Commands:"
        echo "  status, s       - Show connection status for all salons"
        echo "  qr, q          - Show QR code links for unconnected salons"
        echo "  reset <salon>  - Reset connection for specific salon (salon_a, salon_b, salon_c)"
        echo "  reset-all      - Reset connections for all salons"
        echo "  help, h        - Show this help message"
        echo ""
        echo "📱 Examples:"
        echo "  ./manage-connections.sh status"
        echo "  ./manage-connections.sh reset salon_a"
        echo "  ./manage-connections.sh reset-all"
        echo "  ./manage-connections.sh qr"
        ;;
    *)
        echo "❌ Unknown command: $1"
        echo "💡 Use './manage-connections.sh help' for usage information"
        exit 1
        ;;
esac 