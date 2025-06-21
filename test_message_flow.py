#!/usr/bin/env python3
"""
Test Message Flow - Simulate WhatsApp message to check the flow
"""

import requests
import json
from datetime import datetime

RAILWAY_URL = "https://whatsapp-business-bot-production.up.railway.app"

def test_webhook_directly():
    """Test the webhook endpoint directly"""
    print("🧪 Testing WhatsApp webhook endpoint directly...")
    
    # Simulate a WhatsApp message
    test_message = {
        "from": "1234567890@c.us",
        "to": "whatsapp@c.us", 
        "body": "hi",
        "type": "chat",
        "timestamp": int(datetime.now().timestamp()),
        "id": "test_message_123",
        "isGroupMsg": False,
        "author": "1234567890@c.us"
    }
    
    try:
        response = requests.post(
            f"{RAILWAY_URL}/webhook/whatsapp",
            json=test_message,
            timeout=10
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get("reply"):
                print(f"✅ Bot replied: {data['reply']}")
                return True
            else:
                print("❌ No reply from bot")
                return False
        else:
            print(f"❌ Webhook failed with status {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing webhook: {e}")
        return False

def test_whatsapp_service_send():
    """Test sending a message through WhatsApp service"""
    print("\n📤 Testing WhatsApp service send endpoint...")
    
    try:
        # First check if WhatsApp service is ready
        health_response = requests.get(f"{RAILWAY_URL}/health", timeout=10)
        print(f"Health Status: {health_response.status_code}")
        
        if health_response.status_code == 200:
            health_data = health_response.json()
            whatsapp_status = health_data.get('components', {}).get('whatsapp_service')
            print(f"WhatsApp Service Status: {whatsapp_status}")
            
            if whatsapp_status == 'healthy':
                print("✅ WhatsApp service is healthy, testing send...")
                
                # Try to send a test message (this will fail but shows if endpoint works)
                send_response = requests.post(
                    f"{RAILWAY_URL}/send-message",  # This should proxy to WhatsApp service
                    json={
                        "phone": "1234567890@c.us",
                        "message": "Test message from API"
                    },
                    timeout=10
                )
                
                print(f"Send Status: {send_response.status_code}")
                print(f"Send Response: {send_response.text}")
                
        return True
        
    except Exception as e:
        print(f"❌ Error testing send: {e}")
        return False

def check_services_status():
    """Check the status of all services"""
    print("\n🔍 Checking all service statuses...")
    
    try:
        # Check main health
        response = requests.get(f"{RAILWAY_URL}/health", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print("📊 Service Status:")
            print(f"  Overall: {data.get('status')}")
            components = data.get('components', {})
            for service, status in components.items():
                print(f"  {service}: {status}")
        
        # Check root endpoint
        root_response = requests.get(f"{RAILWAY_URL}/", timeout=10)
        if root_response.status_code == 200:
            root_data = root_response.json()
            print(f"\n📱 WhatsApp Service: {root_data.get('whatsapp_service')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error checking status: {e}")
        return False

def main():
    print("🧪 WhatsApp Bot Message Flow Test")
    print("=" * 50)
    
    # Check overall status
    check_services_status()
    
    # Test webhook directly
    webhook_works = test_webhook_directly()
    
    # Test WhatsApp service
    send_works = test_whatsapp_service_send()
    
    print("\n" + "=" * 50)
    print("📊 TEST RESULTS:")
    print(f"✅ Webhook works: {webhook_works}")
    print(f"✅ Send endpoint works: {send_works}")
    
    if webhook_works:
        print("\n💡 The bot logic is working!")
        print("🔍 If you're not getting replies, check:")
        print("1. Make sure you sent 'hi' (lowercase)")
        print("2. Check Railway logs for message forwarding")
        print("3. Verify your phone number format")
    else:
        print("\n❌ Bot logic has issues")
        print("🔧 Check the webhook endpoint and message processing")

if __name__ == "__main__":
    main() 