#!/usr/bin/env python3
"""
Continuous Railway Monitoring
Monitor until WhatsApp service is ready and QR code is available
"""

import requests
import time
from datetime import datetime

RAILWAY_URL = "https://whatsapp-business-bot-production.up.railway.app"

def check_qr_ready():
    """Check if QR code is ready"""
    try:
        response = requests.get(f"{RAILWAY_URL}/qr", timeout=10)
        return response.status_code == 200
    except:
        return False

def check_whatsapp_status():
    """Get WhatsApp service status"""
    try:
        response = requests.get(f"{RAILWAY_URL}/health", timeout=10)
        if response.status_code == 200:
            data = response.json()
            components = data.get('components', {})
            return components.get('whatsapp_service') == 'healthy'
        return False
    except:
        return False

def main():
    print("🔄 Monitoring Railway Deployment...")
    print(f"🌐 URL: {RAILWAY_URL}")
    print("⏰ Checking every 30 seconds until ready...")
    print("🛑 Press Ctrl+C to stop monitoring")
    print("=" * 60)
    
    attempt = 1
    
    while True:
        try:
            current_time = datetime.now().strftime("%H:%M:%S")
            print(f"\n[{current_time}] 🔍 Check #{attempt}")
            
            # Check WhatsApp service
            whatsapp_ready = check_whatsapp_status()
            print(f"   📱 WhatsApp Service: {'✅ Ready' if whatsapp_ready else '⏳ Initializing'}")
            
            # Check QR code
            qr_ready = check_qr_ready()
            print(f"   📋 QR Code Page: {'✅ Available' if qr_ready else '❌ Not ready'}")
            
            if whatsapp_ready and qr_ready:
                print("\n" + "🎉" * 20)
                print("🎉 RAILWAY DEPLOYMENT IS READY! 🎉")
                print("🎉" * 20)
                print(f"\n📱 QR Code URL: {RAILWAY_URL}/qr")
                print("📝 Next Steps:")
                print("1. Visit the QR code URL")
                print("2. Scan with your WhatsApp mobile app")
                print("3. Start chatting with your bot!")
                break
            
            attempt += 1
            print(f"   ⏰ Waiting 30 seconds before next check...")
            time.sleep(30)
            
        except KeyboardInterrupt:
            print("\n\n🛑 Monitoring stopped by user")
            print(f"🔗 You can manually check: {RAILWAY_URL}/qr")
            break
        except Exception as e:
            print(f"   ❌ Error: {e}")
            time.sleep(30)

if __name__ == "__main__":
    main() 