import os
import json
import logging
import requests
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Any
from pydantic import BaseModel

from app.config import get_settings

# Define models inline since we removed the separate models file
class Service(BaseModel):
    """Service model"""
    id: str
    name: str
    duration: int  # in minutes
    price: float
    description: str = ""

class Barber(BaseModel):
    """Barber model"""
    name: str
    email: str = ""
    services: List[str] = []  # List of service IDs
    working_days: List[str] = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday"]
    specialties: List[str] = []
    experience_years: int = 0

class Booking(BaseModel):
    """Booking model"""
    booking_id: str
    service_id: str
    service_name: str
    barber_name: str
    phone: str
    contact_name: str
    date: str  # YYYY-MM-DD format
    time_slot: str
    status: str = "confirmed"
    created_at: str
    source: str = "whatsapp"

logger = logging.getLogger(__name__)
settings = get_settings()

# Firebase configuration
FIREBASE_CONFIG = {
    "apiKey": "AIzaSyDUQnWbTFTIVYX7V0Hv-j-VG9sDrilLCYE",
    "authDomain": "appointment-booking-4c50f.firebaseapp.com",
    "projectId": "appointment-booking-4c50f",
    "storageBucket": "appointment-booking-4c50f.firebasestorage.app",
    "messagingSenderId": "625375458112",
    "appId": "1:625375458112:web:e78b9ceb1337880aaf80a5",
    "measurementId": "G-WN4KZQXN33"
}

PROJECT_ID = FIREBASE_CONFIG["projectId"]
API_KEY = FIREBASE_CONFIG["apiKey"]
BASE_URL = f"https://firestore.googleapis.com/v1/projects/{PROJECT_ID}/databases/(default)/documents"

# Global Firebase client
_firebase_client = None
_firebase_connected = False

# In-memory storage as fallback
_in_memory_storage = {
    'services': {},
    'barbers': {},
    'bookings': {}
}

def initialize_firebase():
    """Initialize Firebase connection using multiple methods"""
    global _firebase_client, _firebase_connected
    
    if _firebase_connected:
        return _firebase_client
    
    logger.info("🔥 Attempting to connect to Firebase...")
    
    # Method 1: Try Firebase Admin SDK with service account
    try:
        import firebase_admin
        from firebase_admin import credentials, firestore
        import base64
        import tempfile
        
        # Check if already initialized
        try:
            app = firebase_admin.get_app()
            logger.info("✅ Firebase Admin already initialized")
        except ValueError:
            # Not initialized, try to initialize
            cred = None
            
            # Option A: Base64 encoded credentials (for Railway/cloud deployment)
            if os.environ.get('FIREBASE_CREDENTIALS_BASE64'):
                try:
                    logger.info("🔧 Using base64 encoded credentials from environment")
                    encoded_creds = os.environ.get('FIREBASE_CREDENTIALS_BASE64')
                    decoded_creds = base64.b64decode(encoded_creds).decode('utf-8')
                    cred_data = json.loads(decoded_creds)
                    
                    # Validate credentials
                    if (cred_data.get('type') == 'service_account' and 
                        'dummy' not in cred_data.get('private_key_id', '') and
                        cred_data.get('project_id') == PROJECT_ID):
                        
                        # Create temporary file for credentials
                        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
                            json.dump(cred_data, temp_file)
                            temp_file_path = temp_file.name
                        
                        cred = credentials.Certificate(temp_file_path)
                        logger.info("✅ Base64 credentials decoded and loaded successfully")
                        
                        # Clean up temp file
                        os.unlink(temp_file_path)
                    else:
                        logger.warning("⚠️ Base64 credentials contain dummy/invalid data")
                        raise Exception("Invalid base64 credentials")
                except Exception as e:
                    logger.warning(f"⚠️ Failed to decode base64 credentials: {str(e)}")
            
            # Option B: Service account file
            elif os.path.exists(settings.FIREBASE_CREDENTIALS_PATH):
                logger.info(f"📄 Using service account from {settings.FIREBASE_CREDENTIALS_PATH}")
                # Check if the file contains valid JSON
                try:
                    with open(settings.FIREBASE_CREDENTIALS_PATH, 'r') as f:
                        cred_data = json.load(f)
                    
                    # Check if it's a real service account key (not dummy)
                    if (cred_data.get('type') == 'service_account' and 
                        'dummy' not in cred_data.get('private_key_id', '') and
                        cred_data.get('project_id') == PROJECT_ID):
                        cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
                    else:
                        logger.warning("⚠️ Service account file contains dummy/invalid credentials")
                        raise Exception("Invalid service account credentials")
                except json.JSONDecodeError:
                    logger.warning("⚠️ Service account file is not valid JSON")
                    raise Exception("Invalid JSON in service account file")
            
            # Option C: Application default credentials
            else:
                logger.info("🔧 Using application default credentials")
                cred = credentials.ApplicationDefault()
            
            # Initialize Firebase
            if cred:
                firebase_admin.initialize_app(cred, {
                    'projectId': PROJECT_ID,
                })
            else:
                raise Exception("No valid credentials found")
        
        _firebase_client = firestore.client()
        
        # Test connection with a simple read operation
        try:
            # Try to access a collection (this will fail gracefully if no permissions)
            collections = _firebase_client.collections()
            test_collection = _firebase_client.collection('_connection_test')
            # Just getting the collection reference doesn't require permissions
            _firebase_connected = True
            logger.info("🎉 Firebase Admin SDK connected successfully!")
            return _firebase_client
        except Exception as test_error:
            logger.warning(f"⚠️ Firebase Admin SDK connection test failed: {str(test_error)}")
            raise test_error
        
    except Exception as e:
        logger.warning(f"⚠️ Firebase Admin SDK failed: {str(e)}")
    
    # Method 2: Try Google Cloud Firestore client
    try:
        from google.cloud import firestore
        from google.auth import default
        
        logger.info("🔧 Trying Google Cloud Firestore client...")
        credentials, project = default()
        _firebase_client = firestore.Client(project=PROJECT_ID, credentials=credentials)
        
        # Test connection
        try:
            test_collection = _firebase_client.collection('_connection_test')
            _firebase_connected = True
            logger.info("🎉 Google Cloud Firestore client connected successfully!")
            return _firebase_client
        except Exception as test_error:
            logger.warning(f"⚠️ Google Cloud Firestore client connection test failed: {str(test_error)}")
            raise test_error
        
    except Exception as e:
        logger.warning(f"⚠️ Google Cloud Firestore client failed: {str(e)}")
    
    # All methods failed - Firebase connection not available
    logger.error("❌ All Firebase connection methods failed")
    logger.info("🔄 The web API key provided doesn't have server-side permissions")
    logger.info("💡 To connect to Firebase, you need:")
    logger.info("   1. A valid service account key file (firebase-key.json), OR")
    logger.info("   2. Base64 encoded credentials in FIREBASE_CREDENTIALS_BASE64 env var, OR")
    logger.info("   3. Google Cloud SDK configured with proper credentials")
    logger.info("🔄 Falling back to in-memory storage with no data")
    _firebase_connected = False
    return None

def is_firebase_connected():
    """Check if Firebase is connected"""
    return _firebase_connected

def get_firebase_client():
    """Get Firebase client, initializing if needed"""
    global _firebase_client
    if not _firebase_connected:
        _firebase_client = initialize_firebase()
    return _firebase_client

def get_all_services():
    """Get all services from Firebase or fallback storage"""
    try:
        if is_firebase_connected():
            logger.info("📋 Getting services from Firebase...")
            client = get_firebase_client()
            
            if client == "REST_API":
                # Use REST API
                response = requests.get(f"{BASE_URL}/services?key={API_KEY}")
                if response.status_code == 200:
                    data = response.json()
                    services = []
                    if 'documents' in data:
                        for doc in data['documents']:
                            service_data = {}
                            for field, value in doc['fields'].items():
                                if 'stringValue' in value:
                                    service_data[field] = value['stringValue']
                                elif 'doubleValue' in value:
                                    service_data[field] = float(value['doubleValue'])
                                elif 'integerValue' in value:
                                    service_data[field] = int(value['integerValue'])
                            if service_data:
                                services.append(Service(**service_data))
                    logger.info(f"✅ Retrieved {len(services)} services from Firebase REST API")
                    return services
            else:
                # Use Firebase Admin SDK
                services_ref = client.collection('services')
                docs = services_ref.stream()
                services = []
                for doc in docs:
                    service_data = doc.to_dict()
                    services.append(Service(**service_data))
                logger.info(f"✅ Retrieved {len(services)} services from Firebase")
                return services
        
        # Fallback to hardcoded data only if Firebase is not connected
        logger.info("📋 Getting services from fallback storage (Firebase not connected)...")
        return _get_default_services()
        
    except Exception as e:
        logger.error(f"❌ Error getting services: {str(e)}")
        logger.info("🔄 Falling back to default services")
        return _get_default_services()

def get_service(service_id: str):
    """Get a specific service by ID"""
    try:
        if is_firebase_connected():
            logger.info(f"🔍 Getting service {service_id} from Firebase...")
            client = get_firebase_client()
            
            if client == "REST_API":
                # Use REST API
                response = requests.get(f"{BASE_URL}/services/{service_id}?key={API_KEY}")
                if response.status_code == 200:
                    data = response.json()
                    service_data = {}
                    for field, value in data['fields'].items():
                        if 'stringValue' in value:
                            service_data[field] = value['stringValue']
                        elif 'doubleValue' in value:
                            service_data[field] = float(value['doubleValue'])
                        elif 'integerValue' in value:
                            service_data[field] = int(value['integerValue'])
                    logger.info(f"✅ Found service: {service_data.get('name', 'Unknown')}")
                    return Service(**service_data)
            else:
                # Use Firebase Admin SDK
                service_ref = client.collection('services').document(service_id)
                doc = service_ref.get()
                if doc.exists:
                    service_data = doc.to_dict()
                    logger.info(f"✅ Found service: {service_data['name']}")
                    return Service(**service_data)
                    
        # Fallback to hardcoded data only if Firebase is not connected
        logger.info(f"🔍 Getting service {service_id} from fallback storage...")
        services = _get_default_services()
        for service in services:
            if service.id == service_id:
                return service
        
        logger.warning(f"❌ Service {service_id} not found")
        return None
        
    except Exception as e:
        logger.error(f"❌ Error getting service {service_id}: {str(e)}")
        return None

def get_all_barbers():
    """Get all barbers from Firebase or fallback storage"""
    try:
        if is_firebase_connected():
            logger.info("👥 Getting barbers from Firebase...")
            client = get_firebase_client()
            
            if client == "REST_API":
                # Use REST API
                response = requests.get(f"{BASE_URL}/barbers?key={API_KEY}")
                if response.status_code == 200:
                    data = response.json()
                    barbers = []
                    if 'documents' in data:
                        for doc in data['documents']:
                            barber_data = {}
                            for field, value in doc['fields'].items():
                                if 'stringValue' in value:
                                    barber_data[field] = value['stringValue']
                                elif 'arrayValue' in value:
                                    barber_data[field] = [item['stringValue'] for item in value['arrayValue'].get('values', [])]
                                elif 'integerValue' in value:
                                    barber_data[field] = int(value['integerValue'])
                            if barber_data:
                                barbers.append(Barber(**barber_data))
                    logger.info(f"✅ Retrieved {len(barbers)} barbers from Firebase REST API")
                    return barbers
            else:
                # Use Firebase Admin SDK
                barbers_ref = client.collection('barbers')
                docs = barbers_ref.stream()
                barbers = []
                for doc in docs:
                    barber_data = doc.to_dict()
                    barbers.append(Barber(**barber_data))
                logger.info(f"✅ Retrieved {len(barbers)} barbers from Firebase")
                return barbers
        
        # Fallback to hardcoded data only if Firebase is not connected
        logger.info("👥 Getting barbers from fallback storage (Firebase not connected)...")
        return _get_default_barbers()
        
    except Exception as e:
        logger.error(f"❌ Error getting barbers: {str(e)}")
        logger.info("🔄 Falling back to default barbers")
        return _get_default_barbers()

def get_barbers_for_service(service_id: str):
    """Get all barbers that provide a specific service"""
    try:
        if is_firebase_connected():
            logger.info(f"🔍 Getting barbers for service {service_id} from Firebase...")
            client = get_firebase_client()
            
            if client == "REST_API":
                # Use REST API - get all barbers and filter
                all_barbers = get_all_barbers()
                barbers = [b for b in all_barbers if service_id in b.services]
            else:
                # Use Firebase Admin SDK with query
                barbers_ref = client.collection('barbers')
                query = barbers_ref.where('services', 'array_contains', service_id)
                docs = query.stream()
                barbers = []
                for doc in docs:
                    barber_data = doc.to_dict()
                    barbers.append(Barber(**barber_data))
            
            logger.info(f"✅ Found {len(barbers)} barbers for service {service_id}")
            return barbers
        
        # Fallback to hardcoded data only if Firebase is not connected
        logger.info(f"🔍 Getting barbers for service {service_id} from fallback storage...")
        all_barbers = _get_default_barbers()
        barbers = [b for b in all_barbers if service_id in b.services]
        logger.info(f"✅ Found {len(barbers)} barbers for service {service_id}")
        return barbers
        
    except Exception as e:
        logger.error(f"❌ Error getting barbers for service {service_id}: {str(e)}")
        return []

def get_available_slots(barber_name: str, date: datetime = None) -> List[str]:
    """Get available slots for a barber on a specific date"""
    if not date:
        date = datetime.now()
    
    date_str = date.strftime("%Y-%m-%d")
    
    try:
        logger.info(f"📅 Getting available slots for {barber_name} on {date_str}...")
        
        # Get bookings for this barber on this date
        booked_slots = []
        
        if is_firebase_connected():
            client = get_firebase_client()
            
            if client == "REST_API":
                # Use REST API to get bookings
                response = requests.get(f"{BASE_URL}/bookings?key={API_KEY}")
                if response.status_code == 200:
                    data = response.json()
                    if 'documents' in data:
                        for doc in data['documents']:
                            booking_data = {}
                            for field, value in doc['fields'].items():
                                if 'stringValue' in value:
                                    booking_data[field] = value['stringValue']
                            
                            if (booking_data.get('barber_name') == barber_name and 
                                booking_data.get('date') == date_str):
                                booked_slots.append(booking_data.get('time_slot'))
            else:
                # Use Firebase Admin SDK
                bookings_ref = client.collection('bookings')
                query = bookings_ref.where('barber_name', '==', barber_name).where('date', '==', date_str)
                docs = query.stream()
                for doc in docs:
                    booking_data = doc.to_dict()
                    booked_slots.append(booking_data.get('time_slot'))
        else:
            # Use in-memory storage
            for booking_data in _in_memory_storage['bookings'].values():
                if (booking_data.get('barber_name') == barber_name and 
                    booking_data.get('date') == date_str):
                    booked_slots.append(booking_data.get('time_slot'))
        
        logger.info(f"📋 Found {len(booked_slots)} existing bookings for {barber_name} on {date_str}")
        
        # Generate all possible slots (9 AM to 5 PM, 30-min intervals)
        all_slots = []
        current_time = datetime.strptime("09:00", "%H:%M")
        end_time = datetime.strptime("17:00", "%H:%M")
        
        while current_time < end_time:
            slot = current_time.strftime("%I:%M %p")
            if slot not in booked_slots:
                all_slots.append(slot)
            current_time += timedelta(minutes=30)
        
        logger.info(f"✅ {len(all_slots)} available slots for {barber_name} on {date_str}")
        return all_slots
        
    except Exception as e:
        logger.error(f"❌ Error getting available slots: {str(e)}")
        # Return default slots if error
        all_slots = []
        current_time = datetime.strptime("09:00", "%H:%M")
        end_time = datetime.strptime("17:00", "%H:%M")
        
        while current_time < end_time:
            slot = current_time.strftime("%I:%M %p")
            all_slots.append(slot)
            current_time += timedelta(minutes=30)
        
        return all_slots

def book_slot(booking_data: Dict) -> Dict[str, str]:
    """Book a slot for a barber"""
    try:
        logger.info(f"📝 Creating booking...")
        
        # Add date if not provided
        if 'date' not in booking_data:
            booking_data['date'] = datetime.now().strftime("%Y-%m-%d")
            
        # Check if slot is available
        available_slots = get_available_slots(
            booking_data['barber_name'], 
            datetime.strptime(booking_data['date'], "%Y-%m-%d")
        )
        
        if booking_data['time_slot'] not in available_slots:
            logger.warning(f"❌ Time slot {booking_data['time_slot']} not available")
            return {
                'status': 'error',
                'message': 'This time slot is not available'
            }
            
        # Add booking metadata
        booking_data['status'] = 'confirmed'
        booking_data['source'] = 'whatsapp'
        booking_data['created_at'] = datetime.now().isoformat()
        
        # Generate unique booking ID
        import time
        booking_id = f"booking_{int(time.time())}"
        booking_data['booking_id'] = booking_id
        
        if is_firebase_connected():
            client = get_firebase_client()
            
            if client == "REST_API":
                # Use REST API to save booking
                firestore_data = {
                    "fields": {}
                }
                for key, value in booking_data.items():
                    firestore_data["fields"][key] = {"stringValue": str(value)}
                
                response = requests.post(
                    f"{BASE_URL}/bookings/{booking_id}?key={API_KEY}",
                    json=firestore_data
                )
                
                if response.status_code in [200, 201]:
                    logger.info(f"✅ Booking saved to Firebase via REST API with ID: {booking_id}")
                else:
                    raise Exception(f"REST API failed with status {response.status_code}")
            else:
                # Use Firebase Admin SDK
                booking_ref = client.collection('bookings').document(booking_id)
                booking_ref.set(booking_data)
                logger.info(f"✅ Booking saved to Firebase with ID: {booking_id}")
        else:
            # Save to in-memory storage
            _in_memory_storage['bookings'][booking_id] = booking_data.copy()
            logger.info(f"✅ Booking saved to in-memory storage with ID: {booking_id}")
        
        logger.info(f"📋 Booking details: {booking_data['contact_name']} - {booking_data['service_name']} with {booking_data['barber_name']} at {booking_data['time_slot']}")
        
        return {
            'status': 'success',
            'message': 'Booking confirmed successfully',
            'booking_id': booking_id
        }
        
    except Exception as e:
        logger.error(f"❌ Error saving booking: {str(e)}")
        return {
            'status': 'error',
            'message': f'Failed to save booking: {str(e)}'
        }

def get_all_bookings():
    """Get all bookings (for debugging)"""
    try:
        logger.info("📋 Getting all bookings...")
        bookings = []
        
        if is_firebase_connected():
            client = get_firebase_client()
            
            if client == "REST_API":
                response = requests.get(f"{BASE_URL}/bookings?key={API_KEY}")
                if response.status_code == 200:
                    data = response.json()
                    if 'documents' in data:
                        for doc in data['documents']:
                            booking_data = {}
                            for field, value in doc['fields'].items():
                                if 'stringValue' in value:
                                    booking_data[field] = value['stringValue']
                            if booking_data:
                                bookings.append(booking_data)
            else:
                bookings_ref = client.collection('bookings')
                docs = bookings_ref.stream()
                for doc in docs:
                    booking_data = doc.to_dict()
                    booking_data['id'] = doc.id
                    bookings.append(booking_data)
        else:
            # Use in-memory storage
            for booking_id, booking_data in _in_memory_storage['bookings'].items():
                booking_data_copy = booking_data.copy()
                booking_data_copy['id'] = booking_id
                bookings.append(booking_data_copy)
        
        logger.info(f"✅ Retrieved {len(bookings)} bookings")
        return bookings
        
    except Exception as e:
        logger.error(f"❌ Error getting bookings: {str(e)}")
        return []

def _get_default_services():
    """Get default services (empty when Firebase is not connected)"""
    logger.warning("⚠️ No Firebase connection - no services available")
    return []

def _get_default_barbers():
    """Get default barbers (empty when Firebase is not connected)"""
    logger.warning("⚠️ No Firebase connection - no barbers available")
    return []

def init_default_data():
    """Initialize data only if Firebase is connected"""
    if is_firebase_connected():
        logger.info("🔥 Firebase is connected - checking if data exists in database...")
        
        # Check if data already exists in Firebase
        services = get_all_services()
        barbers = get_all_barbers()
        
        if not services or not barbers:
            logger.info("📝 No data found in Firebase - please add data through Firebase console or admin interface")
            logger.info("💡 The system requires Firebase connection to function properly")
        else:
            logger.info(f"✅ Data already exists in Firebase: {len(services)} services, {len(barbers)} barbers")
    else:
        logger.warning("🔄 Firebase not connected - system will have no data available")
        logger.info("💡 To use the booking system, you need:")
        logger.info("   1. A valid Firebase service account key file (firebase-key.json), OR")
        logger.info("   2. Google Cloud SDK configured with proper credentials")
        logger.info("   3. Data populated in your Firebase database")

# Initialize Firebase connection on import
initialize_firebase() 