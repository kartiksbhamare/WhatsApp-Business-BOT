#!/usr/bin/env python3
"""
Test Firebase connection and create sample data
"""

import os
import sys
from datetime import datetime

def test_firebase_with_key():
    """Test Firebase connection with service account key"""
    if not os.path.exists('firebase-key.json'):
        return False, "firebase-key.json not found"
    
    try:
        import firebase_admin
        from firebase_admin import credentials, firestore
        
        if not firebase_admin._apps:
            cred = credentials.Certificate('firebase-key.json')
            firebase_admin.initialize_app(cred)
        
        db = firestore.client()
        
        # Test connection by trying to read from a collection
        test_ref = db.collection('test').limit(1)
        list(test_ref.stream())
        
        return True, db
    except Exception as e:
        return False, f"Error with service account key: {e}"

def test_firebase_default_credentials():
    """Test Firebase connection with default credentials"""
    try:
        import firebase_admin
        from firebase_admin import credentials, firestore
        
        if not firebase_admin._apps:
            cred = credentials.ApplicationDefault()
            firebase_admin.initialize_app(cred, {
                'projectId': 'appointment-booking-4c50f'
            })
        
        db = firestore.client()
        
        # Test connection
        test_ref = db.collection('test').limit(1)
        list(test_ref.stream())
        
        return True, db
    except Exception as e:
        return False, f"Error with default credentials: {e}"

def clean_and_populate_database(db):
    """Clean existing data and populate with sample data"""
    print("🧹 Cleaning existing data...")
    
    # Clean collections
    collections = ['services', 'barbers', 'salons', 'bookings']
    
    for collection_name in collections:
        docs = db.collection(collection_name).stream()
        deleted_count = 0
        for doc in docs:
            doc.reference.delete()
            deleted_count += 1
        if deleted_count > 0:
            print(f"   Deleted {deleted_count} documents from {collection_name}")

    print("\n🏢 Creating salon...")
    salon_data = {
        'id': 'main_salon',
        'name': 'Beauty Salon',
        'address': '123 Main Street, City, State 12345',
        'phone': '+1-555-123-4567',
        'email': 'info@beautysalon.com',
        'hours': {
            'monday': '9:00 AM - 6:00 PM',
            'tuesday': '9:00 AM - 6:00 PM',
            'wednesday': '9:00 AM - 6:00 PM',
            'thursday': '9:00 AM - 6:00 PM',
            'friday': '9:00 AM - 7:00 PM',
            'saturday': '8:00 AM - 5:00 PM',
            'sunday': 'Closed'
        },
        'created_at': datetime.now().isoformat(),
        'active': True
    }
    db.collection('salons').document('main_salon').set(salon_data)
    print("   ✅ Created main salon")

    print("\n💇 Creating services...")
    services = [
        {
            'id': 'haircut',
            'name': 'Hair Cut',
            'description': 'Professional hair cutting and styling',
            'duration': 45,
            'price': 35.00,
            'category': 'Hair Services',
            'salon_id': 'main_salon',
            'active': True
        },
        {
            'id': 'hair_color',
            'name': 'Hair Color',
            'description': 'Full hair coloring service',
            'duration': 120,
            'price': 85.00,
            'category': 'Hair Services',
            'salon_id': 'main_salon',
            'active': True
        },
        {
            'id': 'manicure',
            'name': 'Manicure',
            'description': 'Complete nail care and polish',
            'duration': 60,
            'price': 25.00,
            'category': 'Nail Services',
            'salon_id': 'main_salon',
            'active': True
        },
        {
            'id': 'pedicure',
            'name': 'Pedicure',
            'description': 'Complete foot and nail care',
            'duration': 75,
            'price': 35.00,
            'category': 'Nail Services',
            'salon_id': 'main_salon',
            'active': True
        },
        {
            'id': 'facial',
            'name': 'Facial Treatment',
            'description': 'Deep cleansing facial therapy',
            'duration': 90,
            'price': 65.00,
            'category': 'Skin Care',
            'salon_id': 'main_salon',
            'active': True
        }
    ]
    
    for service in services:
        db.collection('services').document(service['id']).set(service)
        print(f"   ✅ Created service: {service['name']} - ${service['price']}")

    print("\n👨‍💼 Creating barbers...")
    barbers = [
        {
            'name': 'Maya Rodriguez',
            'email': 'maya@beautysalon.com',
            'phone': '+1-555-123-4568',
            'salon_id': 'main_salon',
            'services': ['haircut', 'hair_color', 'facial'],
            'specialties': ['Hair Styling', 'Color Specialist', 'Facial Treatments'],
            'experience_years': 8,
            'working_days': ['monday', 'tuesday', 'wednesday', 'thursday', 'friday'],
            'working_hours': {
                'start': '09:00',
                'end': '17:00'
            },
            'bio': 'Expert hair stylist with 8 years of experience in modern cuts and color techniques.',
            'active': True,
            'created_at': datetime.now().isoformat()
        },
        {
            'name': 'Alex Chen',
            'email': 'alex@beautysalon.com',
            'phone': '+1-555-123-4569',
            'salon_id': 'main_salon',
            'services': ['haircut', 'manicure', 'pedicure'],
            'specialties': ['Precision Cuts', 'Nail Art', 'Nail Care'],
            'experience_years': 5,
            'working_days': ['tuesday', 'wednesday', 'thursday', 'friday', 'saturday'],
            'working_hours': {
                'start': '10:00',
                'end': '18:00'
            },
            'bio': 'Skilled in both hair cutting and nail services with attention to detail.',
            'active': True,
            'created_at': datetime.now().isoformat()
        },
        {
            'name': 'Sarah Johnson',
            'email': 'sarah@beautysalon.com',
            'phone': '+1-555-123-4570',
            'salon_id': 'main_salon',
            'services': ['facial', 'manicure', 'pedicure'],
            'specialties': ['Skin Care', 'Spa Treatments', 'Relaxation Therapy'],
            'experience_years': 6,
            'working_days': ['monday', 'wednesday', 'friday', 'saturday'],
            'working_hours': {
                'start': '09:00',
                'end': '16:00'
            },
            'bio': 'Certified esthetician specializing in facial treatments and spa services.',
            'active': True,
            'created_at': datetime.now().isoformat()
        }
    ]
    
    for barber in barbers:
        doc_id = barber['name'].lower().replace(' ', '_')
        db.collection('barbers').document(doc_id).set(barber)
        print(f"   ✅ Created barber: {barber['name']} - {', '.join(barber['specialties'])}")

def main():
    print("🔥 Firebase Connection Test & Database Setup")
    print("=" * 50)
    
    # Try service account key first
    success, result = test_firebase_with_key()
    if success:
        print("✅ Connected to Firebase using service account key!")
        db = result
    else:
        print(f"❌ Service account key failed: {result}")
        print("\n🔄 Trying default credentials...")
        
        success, result = test_firebase_default_credentials()
        if success:
            print("✅ Connected to Firebase using default credentials!")
            db = result
        else:
            print(f"❌ Default credentials failed: {result}")
            print("\n📋 To fix this, you need to:")
            print("1. Create firebase-key.json using Firebase Console:")
            print("   https://console.firebase.google.com/project/appointment-booking-4c50f/settings/serviceaccounts/adminsdk")
            print("2. Or install gcloud CLI and authenticate:")
            print("   curl https://sdk.cloud.google.com | bash")
            print("   gcloud auth application-default login")
            return
    
    print("\n🎯 Proceeding with database setup...")
    
    try:
        clean_and_populate_database(db)
        
        print("\n🎉 Database setup complete!")
        print("\nYour salon now has:")
        print("  - 1 salon: Beauty Salon")
        print("  - 5 services: Hair Cut ($35), Hair Color ($85), Manicure ($25), Pedicure ($35), Facial ($65)")
        print("  - 3 barbers: Maya, Alex, Sarah")
        print("\n✅ You can now test your WhatsApp bot!")
        
    except Exception as e:
        print(f"❌ Error setting up database: {e}")

if __name__ == "__main__":
    main() 