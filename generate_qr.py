#!/usr/bin/env python3
"""
Generate QR Code for WhatsApp Web Authentication
This script creates a scannable QR code image from WhatsApp Web session data.
"""

import qrcode
from qrcode import QRCode
import sys
import json
import base64

def generate_qr_code(data, filename="whatsapp_qr.png"):
    """Generate QR code image from data"""
    
    # Create QR code instance
    qr = QRCode(
        version=1,  # Controls size (1 is smallest)
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,  # Size of each box in pixels
        border=4,     # Border size
    )
    
    # Add data to QR code
    qr.add_data(data)
    qr.make(fit=True)
    
    # Create image
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Save image
    img.save(filename)
    print(f"✅ QR code saved as: {filename}")
    print(f"📱 Open this file and scan with WhatsApp mobile app")
    
    return filename

def create_sample_qr():
    """Create a sample QR code for testing"""
    sample_data = "https://web.whatsapp.com/"
    generate_qr_code(sample_data, "sample_qr.png")

if __name__ == "__main__":
    print("🔍 WhatsApp QR Code Generator")
    print("=" * 40)
    
    if len(sys.argv) > 1:
        # Use provided data
        qr_data = sys.argv[1]
        generate_qr_code(qr_data)
    else:
        # Create sample QR
        print("📝 Creating sample QR code...")
        create_sample_qr()
        print("\n💡 To use with real WhatsApp data:")
        print("   python generate_qr.py 'your_whatsapp_qr_data'") 