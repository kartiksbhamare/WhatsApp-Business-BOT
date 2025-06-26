#!/bin/bash

# Smart WhatsApp Booking Bot - Environment Setup Script
# Helps configure environment variables for different deployment scenarios

echo "🔧 Smart WhatsApp Booking Bot - Environment Setup"
echo "=================================================="

# Check if .env already exists
if [ -f ".env" ]; then
    echo "⚠️ .env file already exists!"
    read -p "Do you want to overwrite it? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "❌ Setup cancelled. Existing .env file preserved."
        exit 1
    fi
fi

echo "Please choose your deployment environment:"
echo "1. Local Development (localhost)"
echo "2. Railway Production"
echo "3. Docker Compose"
echo "4. Custom URLs"
echo ""
read -p "Enter your choice (1-4): " choice

case $choice in
    1)
        echo "🏠 Setting up for Local Development..."
        cat > .env << EOF
# Local Development Configuration
BACKEND_URL=http://localhost:8000
WHATSAPP_SERVICE_URL=http://localhost:3000
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000
WHATSAPP_HOST=0.0.0.0
WHATSAPP_PORT=3000
SALON_NAME=Beauty Salon
FIREBASE_PROJECT_ID=appointment-booking-4c50f
FIREBASE_CREDENTIALS_PATH=firebase-key.json
DEBUG=true
LOG_LEVEL=INFO
EOF
        ;;
    2)
        echo "🚂 Setting up for Railway Production..."
        read -p "Enter your Railway app domain (e.g., your-app.railway.app): " railway_domain
        if [ -z "$railway_domain" ]; then
            echo "❌ Railway domain is required!"
            exit 1
        fi
        
        cat > .env << EOF
# Railway Production Configuration
BACKEND_URL=https://$railway_domain
WHATSAPP_SERVICE_URL=https://$railway_domain
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000
WHATSAPP_HOST=0.0.0.0
WHATSAPP_PORT=3000
SALON_NAME=Beauty Salon
FIREBASE_PROJECT_ID=appointment-booking-4c50f
FIREBASE_CREDENTIALS_BASE64=your_base64_credentials_here
RAILWAY_ENVIRONMENT=true
PUPPETEER_EXECUTABLE_PATH=/usr/bin/google-chrome-stable
DEBUG=false
LOG_LEVEL=INFO
EOF
        echo "⚠️ Don't forget to:"
        echo "   1. Replace 'your_base64_credentials_here' with your actual Firebase credentials"
        echo "   2. Run: ./generate_base64_credentials.sh to generate the base64 string"
        ;;
    3)
        echo "🐳 Setting up for Docker Compose..."
        cat > .env << EOF
# Docker Compose Configuration
BACKEND_URL=http://backend:8000
WHATSAPP_SERVICE_URL=http://whatsapp:3000
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000
WHATSAPP_HOST=0.0.0.0
WHATSAPP_PORT=3000
SALON_NAME=Beauty Salon
FIREBASE_PROJECT_ID=appointment-booking-4c50f
FIREBASE_CREDENTIALS_PATH=firebase-key.json
DOCKER_ENV=true
PUPPETEER_EXECUTABLE_PATH=/usr/bin/google-chrome-stable
DEBUG=false
LOG_LEVEL=INFO
EOF
        ;;
    4)
        echo "⚙️ Setting up Custom URLs..."
        read -p "Enter Backend URL (e.g., https://api.yourdomain.com): " backend_url
        read -p "Enter WhatsApp Service URL (e.g., https://whatsapp.yourdomain.com): " whatsapp_url
        read -p "Enter Salon Name: " salon_name
        
        if [ -z "$backend_url" ] || [ -z "$whatsapp_url" ]; then
            echo "❌ Backend URL and WhatsApp Service URL are required!"
            exit 1
        fi
        
        cat > .env << EOF
# Custom Configuration
BACKEND_URL=$backend_url
WHATSAPP_SERVICE_URL=$whatsapp_url
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000
WHATSAPP_HOST=0.0.0.0
WHATSAPP_PORT=3000
SALON_NAME=${salon_name:-Beauty Salon}
FIREBASE_PROJECT_ID=appointment-booking-4c50f
FIREBASE_CREDENTIALS_PATH=firebase-key.json
DEBUG=false
LOG_LEVEL=INFO
EOF
        ;;
    *)
        echo "❌ Invalid choice. Please run the script again."
        exit 1
        ;;
esac

echo ""
echo "✅ Environment configuration created successfully!"
echo "📄 File: .env"
echo ""
echo "🔧 Next steps:"
echo "1. Review the .env file and adjust settings if needed"
echo "2. Make sure your Firebase credentials are in place"
echo "3. Run your application with: ./start_bot.sh"
echo ""
echo "📋 Current configuration:"
cat .env 