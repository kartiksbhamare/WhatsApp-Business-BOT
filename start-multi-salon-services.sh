#!/bin/bash

# Start Multi-Salon WhatsApp Booking Bot Services
echo "🚀 Starting Multi-Salon WhatsApp Booking Bot Services..."
echo "========================================================="

# Function to check if port is already in use
check_port() {
    local port=$1
    local service_name=$2
    
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo "⚠️  Port $port is already in use (${service_name})"
        echo "   Use './stop-multi-salon-services.sh' to stop existing services"
        return 1
    else
        echo "✅ Port $port is available for ${service_name}"
        return 0
    fi
}

# Function to start a service in background
start_service() {
    local command=$1
    local service_name=$2
    local port=$3
    local log_file=$4
    
    echo "🚀 Starting ${service_name} on port ${port}..."
    echo "   Command: ${command}"
    echo "   Logs: ${log_file}"
    
    # Start service in background and redirect output to log file
    nohup $command > $log_file 2>&1 &
    local pid=$!
    
    echo "   PID: ${pid}"
    
    # Wait a moment to check if process is still running
    sleep 2
    if kill -0 $pid 2>/dev/null; then
        echo "   ✅ ${service_name} started successfully"
        return 0
    else
        echo "   ❌ ${service_name} failed to start"
        echo "   Check logs: tail -f ${log_file}"
        return 1
    fi
}

# Check if required files exist
echo "🔍 Checking required files..."
required_files=("whatsapp-service-salon-a.js" "whatsapp-service-salon-b.js" "whatsapp-service-salon-c.js" "app/main.py")

for file in "${required_files[@]}"; do
    if [ ! -f "$file" ]; then
        echo "❌ Required file not found: $file"
        exit 1
    else
        echo "✅ Found: $file"
    fi
done

# Check if node is installed
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed. Please install Node.js first."
    exit 1
else
    echo "✅ Node.js is available: $(node --version)"
fi

# Check if python is installed
if ! command -v python3 &> /dev/null && ! command -v python &> /dev/null; then
    echo "❌ Python is not installed. Please install Python first."
    exit 1
else
    python_cmd=$(command -v python3 || command -v python)
    echo "✅ Python is available: $($python_cmd --version)"
fi

echo ""
echo "🔍 Checking port availability..."

# Check all ports before starting
ports_available=true
check_port 8000 "Backend API" || ports_available=false
check_port 3005 "Salon A WhatsApp" || ports_available=false
check_port 3006 "Salon B WhatsApp" || ports_available=false
check_port 3007 "Salon C WhatsApp" || ports_available=false

if [ "$ports_available" = false ]; then
    echo ""
    echo "❌ Some ports are already in use. Please stop existing services first."
    exit 1
fi

echo ""
echo "🚀 Starting all services..."

# Create logs directory if it doesn't exist
mkdir -p logs

# Start Backend API (FastAPI)
python_cmd=$(command -v python3 || command -v python)
start_service "$python_cmd -m uvicorn app.main:app --host 0.0.0.0 --port 8000" "Backend API" 8000 "logs/backend.log"

# Start Salon WhatsApp Services
start_service "node whatsapp-service-salon-a.js" "Salon A WhatsApp (Downtown Beauty)" 3005 "logs/salon-a.log"
start_service "node whatsapp-service-salon-b.js" "Salon B WhatsApp (Uptown Hair)" 3006 "logs/salon-b.log"
start_service "node whatsapp-service-salon-c.js" "Salon C WhatsApp (Luxury Spa)" 3007 "logs/salon-c.log"

echo ""
echo "🎉 All services started successfully!"
echo ""
echo "🔗 Service URLs:"
echo "📊 Backend API: http://localhost:8000"
echo "📊 Backend Health: http://localhost:8000/health"
echo "📊 API Docs: http://localhost:8000/docs"
echo ""
echo "📱 WhatsApp Services:"
echo "🏢 Salon A (Downtown Beauty): http://localhost:3005/qr"
echo "🏢 Salon B (Uptown Hair): http://localhost:3006/qr"  
echo "🏢 Salon C (Luxury Spa): http://localhost:3007/qr"
echo ""
echo "📋 Management:"
echo "📊 Check status: ./check-multi-salon-status.sh"  
echo "🛑 Stop services: ./stop-multi-salon-services.sh"
echo ""
echo "📝 Log files:"
echo "   Backend: tail -f logs/backend.log"
echo "   Salon A: tail -f logs/salon-a.log"
echo "   Salon B: tail -f logs/salon-b.log"
echo "   Salon C: tail -f logs/salon-c.log"
echo ""
echo "⏳ Services are starting up... Please wait 10-20 seconds before accessing QR codes." 