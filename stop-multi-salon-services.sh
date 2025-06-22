#!/bin/bash

# Stop Multi-Salon Services
echo "🛑 Stopping Multi-Salon WhatsApp Booking Bot Services..."
echo "========================================================="

# Function to stop services on a port
stop_port() {
    local port=$1
    local name=$2
    
    echo "🔍 Checking port $port ($name)..."
    
    # Find process using the port
    pids=$(lsof -ti :$port 2>/dev/null)
    
    if [ -z "$pids" ]; then
        echo "  ℹ️  No process found on port $port"
    else
        echo "  📍 Found processes: $pids"
        for pid in $pids; do
            echo "  ⏹️  Stopping process $pid..."
            kill -TERM $pid 2>/dev/null
            
            # Wait a moment for graceful shutdown
            sleep 2
            
            # Force kill if still running
            if kill -0 $pid 2>/dev/null; then
                echo "  💥 Force killing process $pid..."
                kill -KILL $pid 2>/dev/null
            fi
            
            # Verify it's stopped
            if kill -0 $pid 2>/dev/null; then
                echo "  ❌ Failed to stop process $pid"
            else
                echo "  ✅ Process $pid stopped successfully"
            fi
        done
    fi
    echo ""
}

# Stop all services
echo "🛑 Stopping all services:"
echo ""

stop_port 8000 "Backend API"
stop_port 3005 "Salon A WhatsApp"
stop_port 3006 "Salon B WhatsApp"
stop_port 3007 "Salon C WhatsApp"

# Also look for node processes that might be running
echo "🔍 Checking for remaining Node.js processes..."
node_pids=$(pgrep -f "whatsapp-service-salon" 2>/dev/null)

if [ -z "$node_pids" ]; then
    echo "  ℹ️  No WhatsApp service processes found"
else
    echo "  📍 Found WhatsApp service processes: $node_pids"
    for pid in $node_pids; do
        echo "  ⏹️  Stopping WhatsApp service process $pid..."
        kill -TERM $pid 2>/dev/null
        sleep 1
        if kill -0 $pid 2>/dev/null; then
            kill -KILL $pid 2>/dev/null
        fi
    done
fi

# Check for uvicorn processes
echo ""
echo "🔍 Checking for remaining Python/uvicorn processes..."
uvicorn_pids=$(pgrep -f "uvicorn.*app.main" 2>/dev/null)

if [ -z "$uvicorn_pids" ]; then
    echo "  ℹ️  No uvicorn processes found"
else
    echo "  📍 Found uvicorn processes: $uvicorn_pids"
    for pid in $uvicorn_pids; do
        echo "  ⏹️  Stopping uvicorn process $pid..."
        kill -TERM $pid 2>/dev/null
        sleep 1
        if kill -0 $pid 2>/dev/null; then
            kill -KILL $pid 2>/dev/null
        fi
    done
fi

echo ""
echo "✅ All Multi-Salon services have been stopped!"
echo ""
echo "🔄 To restart: ./start-multi-salon-services.sh"
echo "📊 To check status: ./check-multi-salon-status.sh" 