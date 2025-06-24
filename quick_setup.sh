#!/bin/bash

echo "🚀 Smart WhatsApp Booking Bot - Quick Setup"
echo "==========================================="
echo ""

# Check if firebase-key.json exists
if [ ! -f "firebase-key.json" ]; then
    echo "❌ firebase-key.json not found"
    echo ""
    echo "📋 Please create Firebase service account key:"
    echo "1. Go to: https://console.firebase.google.com/project/appointment-booking-4c50f/settings/serviceaccounts/adminsdk"
    echo "2. Click 'Generate new private key'"
    echo "3. Save as 'firebase-key.json' in this directory"
    echo ""
    echo "Then run this script again: ./quick_setup.sh"
    exit 1
fi

echo "✅ firebase-key.json found!"
echo ""

# Test Firebase connection and populate database
echo "🔥 Testing Firebase connection and populating database..."
python3 test_firebase_connection.py

if [ $? -eq 0 ]; then
    echo ""
    echo "🎉 Database setup complete!"
    echo ""
    echo "🚀 Starting WhatsApp bot..."
    ./start_bot.sh
else
    echo "❌ Database setup failed"
    echo "Please check your firebase-key.json file"
fi 