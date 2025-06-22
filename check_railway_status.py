#!/usr/bin/env python3
"""
Railway Deployment Status Checker
Monitor the WhatsApp service initialization progress
"""

import requests
import time
import json
from datetime import datetime

RAILWAY_URL = "https://whatsapp-business-bot-production.up.railway.app"

def check_main_app():
    """Check if main FastAPI app is responding"""
    try:
        response = requests.get(f"{RAILWAY_URL}/", timeout=10)
        if response.status_code == 200:
            data = response.json()
            return True, data
        else:
            return False, f"Status code: {response.status_code}"
    except Exception as e:
        return False, str(e)

def check_health():
    """Check health endpoint"""
    try:
        response = requests.get(f"{RAILWAY_URL}/health", timeout=10)
        if response.status_code == 200:
            data = response.json()
            return True, data
        else:
            return False, f"Status code: {response.status_code}"
    except Exception as e:
        return False, str(e)

def check_qr_page():
    """Check if QR code page is accessible"""
    try:
        response = requests.get(f"{RAILWAY_URL}/qr", timeout=10)
        if response.status_code == 200:
            return True, "QR page is accessible"
        else:
            return False, f"Status code: {response.status_code}"
    except Exception as e:
        return False, str(e)

def main():
    print("🔍 Railway Deployment Status Checker")
    print("=" * 50)
    print(f"🌐 Checking: {RAILWAY_URL}")
    print("=" * 50)
    
    # Check main app
    print("\n1️⃣ Checking Main FastAPI App...")
    main_ok, main_data = check_main_app()
    if main_ok:
        print("✅ FastAPI is running!")
        print(f"   Status: {main_data.get('status')}")
        print(f"   WhatsApp Service: {main_data.get('whatsapp_service')}")
    else:
        print(f"❌ FastAPI not responding: {main_data}")
    
    # Check health
    print("\n2️⃣ Checking Health Endpoint...")
    health_ok, health_data = check_health()
    if health_ok:
        print("✅ Health check passed!")
        components = health_data.get('components', {})
        print(f"   Overall Status: {health_data.get('status')}")
        print(f"   WhatsApp Service: {components.get('whatsapp_service')}")
        print(f"   Database: {components.get('database')}")
        print(f"   API: {components.get('api')}")
    else:
        print(f"❌ Health check failed: {health_data}")
    
    # Check QR page
    print("\n3️⃣ Checking QR Code Page...")
    qr_ok, qr_data = check_qr_page()
    if qr_ok:
        print("✅ QR code page is accessible!")
        print(f"   URL: {RAILWAY_URL}/qr")
        print("   📱 You can now scan the QR code with WhatsApp!")
    else:
        print(f"❌ QR page not accessible: {qr_data}")
    
    print("\n" + "=" * 50)
    print("📊 SUMMARY")
    print("=" * 50)
    
    if main_ok and health_ok and qr_ok:
        print("🎉 ALL SYSTEMS OPERATIONAL!")
        print(f"🔗 Main App: {RAILWAY_URL}")
        print(f"📱 QR Code: {RAILWAY_URL}/qr")
        print("\n📝 Next Steps:")
        print("1. Visit the QR code URL")
        print("2. Scan with WhatsApp mobile app")
        print("3. Start chatting with your bot!")
    else:
        print("⚠️ Some issues detected:")
        if not main_ok:
            print("   - FastAPI not responding")
        if not health_ok:
            print("   - Health check failing")
        if not qr_ok:
            print("   - QR code page not accessible")
        print("\n💡 The WhatsApp service may still be initializing...")
        print("   Try again in 1-2 minutes.")

if __name__ == "__main__":
    main() 