#!/bin/bash

echo "🔐 Firebase Credentials Base64 Generator"
echo "========================================"

# Check if firebase-key.json exists
if [ ! -f "firebase-key.json" ]; then
    echo "❌ firebase-key.json not found!"
    echo ""
    echo "📋 Please create Firebase service account key first:"
    echo "1. Go to: https://console.firebase.google.com/project/appointment-booking-4c50f/settings/serviceaccounts/adminsdk"
    echo "2. Click 'Generate new private key'"
    echo "3. Save as 'firebase-key.json' in this directory"
    echo ""
    echo "Then run this script again: ./generate_base64_credentials.sh"
    exit 1
fi

echo "✅ firebase-key.json found!"
echo ""

# Generate base64 encoded credentials
echo "🔧 Generating base64 encoded credentials..."
BASE64_CREDS=$(base64 -i firebase-key.json | tr -d '\n')

echo ""
echo "🎉 Base64 credentials generated successfully!"
echo ""
echo "📋 Copy this environment variable to Railway:"
echo "----------------------------------------"
echo "FIREBASE_CREDENTIALS_BASE64=$BASE64_CREDS"
echo "----------------------------------------"
echo ""
echo "🚀 Railway Setup Instructions:"
echo "1. Go to your Railway project dashboard"
echo "2. Navigate to Variables tab"
echo "3. Add new variable:"
echo "   Name: FIREBASE_CREDENTIALS_BASE64"
echo "   Value: (paste the long string above)"
echo "4. Also add these variables:"
echo "   FIREBASE_PROJECT_ID=appointment-booking-4c50f"
echo "   PUPPETEER_EXECUTABLE_PATH=/usr/bin/google-chrome-stable"
echo "   CHROME_BIN=/usr/bin/google-chrome-stable"
echo ""
echo "✅ After setting these variables, redeploy your Railway app!" 