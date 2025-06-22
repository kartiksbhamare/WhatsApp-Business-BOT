from firebase_admin import credentials, firestore, initialize_app
from datetime import datetime, timedelta
from typing import Dict, Optional, List
import os
import json
from app.config import get_settings
from app.models.services import Service, Barber, Salon, Booking
import logging
from google.cloud import firestore

logger = logging.getLogger(__name__)
settings = get_settings()

# Initialize Firebase Admin with credentials
def get_firebase_credentials():
    """Load Firebase credentials from file"""
    try:
        if os.path.exists(settings.FIREBASE_CREDENTIALS_PATH):
            with open(settings.FIREBASE_CREDENTIALS_PATH, 'r') as f:
                creds = json.load(f)
            logger.info(f"Firebase credentials loaded from {settings.FIREBASE_CREDENTIALS_PATH}")
            return creds
        else:
            logger.error(f"Firebase credentials file not found: {settings.FIREBASE_CREDENTIALS_PATH}")
            return None
    except Exception as e:
        logger.error(f"Error loading Firebase credentials: {str(e)}")
        return None

def initialize_firebase():
    """Initialize Firebase with credentials from file"""
    try:
        cred_dict = get_firebase_credentials()
        if not cred_dict:
            logger.warning("No Firebase credentials found. Please set up credentials.")
            return None
            
        cred = credentials.Certificate(cred_dict)
        app = initialize_app(cred)
        return firestore.client()
    except Exception as e:
        logger.error(f"Error initializing Firebase: {str(e)}")
        return None

# Initialize Firestore client safely
def get_firestore_client():
    """Get Firestore client, initializing if needed"""
    try:
        cred_dict = get_firebase_credentials()
        if not cred_dict:
            logger.warning("No Firebase credentials found. Database operations will be disabled.")
            return None
        return firestore.Client.from_service_account_info(cred_dict)
    except Exception as e:
        logger.error(f"Error initializing Firestore client: {str(e)}")
        return None

# Initialize the database client
db = get_firestore_client()

# In-memory mock database for testing
MOCK_DATABASE = {
    "salons": {
        "salon_a": {
            "id": "salon_a",
            "name": "Downtown Beauty Salon",
            "phone": "+1234567890",
            "address": "123 Main Street, Downtown",
            "whatsapp_service_url": "http://localhost:3000",
            "working_hours": {"Monday": "09:00-17:00", "Tuesday": "09:00-17:00", "Wednesday": "09:00-17:00", "Thursday": "09:00-17:00", "Friday": "09:00-17:00", "Saturday": "10:00-16:00"},
            "timezone": "UTC",
            "active": True
        },
        "salon_b": {
            "id": "salon_b",
            "name": "Uptown Hair Studio",
            "phone": "+0987654321",
            "address": "456 Oak Avenue, Uptown",
            "whatsapp_service_url": "http://localhost:3000",
            "working_hours": {"Monday": "10:00-18:00", "Tuesday": "10:00-18:00", "Wednesday": "10:00-18:00", "Thursday": "10:00-18:00", "Friday": "10:00-18:00", "Saturday": "09:00-17:00"},
            "timezone": "UTC",
            "active": True
        },
        "salon_c": {
            "id": "salon_c",
            "name": "Luxury Spa & Salon",
            "phone": "+1122334455",
            "address": "789 Elm Street, Westside",
            "whatsapp_service_url": "http://localhost:3000",
            "working_hours": {"Tuesday": "09:00-17:00", "Wednesday": "09:00-17:00", "Thursday": "09:00-17:00", "Friday": "09:00-17:00", "Saturday": "10:00-18:00", "Sunday": "10:00-16:00"},
            "timezone": "UTC",
            "active": True
        }
    },
    "services": {
        "salon_a_1": {"id": "salon_a_1", "salon_id": "salon_a", "name": "Hair Cut", "duration": 30, "price": 25.00, "description": "Professional hair cutting and styling"},
        "salon_a_2": {"id": "salon_a_2", "salon_id": "salon_a", "name": "Hair Color", "duration": 90, "price": 75.00, "description": "Hair coloring and highlights"},
        "salon_b_1": {"id": "salon_b_1", "salon_id": "salon_b", "name": "Hair Cut", "duration": 30, "price": 25.00, "description": "Professional hair cutting and styling"},
        "salon_b_2": {"id": "salon_b_2", "salon_id": "salon_b", "name": "Hair Color", "duration": 90, "price": 75.00, "description": "Hair coloring and highlights"},
        "salon_c_1": {"id": "salon_c_1", "salon_id": "salon_c", "name": "Hair Cut", "duration": 30, "price": 25.00, "description": "Professional hair cutting and styling"},
        "salon_c_2": {"id": "salon_c_2", "salon_id": "salon_c", "name": "Hair Color", "duration": 90, "price": 75.00, "description": "Hair coloring and highlights"}
    },
    "barbers": {
        "salon_a_maya": {"name": "Maya", "salon_id": "salon_a", "services": ["salon_a_1", "salon_a_2"], "email": "maya@downtownbeauty.com", "working_days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"], "specialties": ["Hair Coloring"], "experience_years": 6},
        "salon_b_aisha": {"name": "Aisha", "salon_id": "salon_b", "services": ["salon_b_1", "salon_b_2"], "email": "aisha@uptownhair.com", "working_days": ["Monday", "Wednesday", "Thursday", "Friday", "Saturday"], "specialties": ["Hair Styling"], "experience_years": 8},
        "salon_c_priya": {"name": "Priya", "salon_id": "salon_c", "services": ["salon_c_1", "salon_c_2"], "email": "priya@luxuryspa.com", "working_days": ["Tuesday", "Friday", "Saturday", "Sunday"], "specialties": ["Spa Treatments"], "experience_years": 7}
    }
}

USE_MOCK_DB = False

def use_mock_database():
    """Check if we should use mock database"""
    global USE_MOCK_DB
    if not db:
        USE_MOCK_DB = True
        logger.warning("Using mock database for testing")
    return USE_MOCK_DB

def get_available_slots(barber_name: str, date: datetime = None, salon_id: str = None) -> List[str]:
    """
    Get available slots for a barber on a specific date
    
    Args:
        barber_name: Name of the barber
        date: Date to check (defaults to today)
        salon_id: Salon ID to filter by
        
    Returns:
        List of available time slots
    """
    if use_mock_database():
        # Return mock available slots for testing
        return ["09:00 AM", "10:00 AM", "11:00 AM", "02:00 PM", "03:00 PM", "04:00 PM"]
    
    if not db:
        logger.error("Database not available. Cannot get available slots.")
        return []
    
    if not date:
        date = datetime.now()
    
    date_str = date.strftime("%Y-%m-%d")
    
    try:
        # Get barber's document
        barber_query = db.collection('barbers').where('name', '==', barber_name)
        if salon_id:
            barber_query = barber_query.where('salon_id', '==', salon_id)
        
        barber_docs = barber_query.get()
        if not barber_docs:
            logger.error(f"Barber {barber_name} not found in salon {salon_id}")
            return []
            
        # Get bookings for this barber on this date
        booking_query = db.collection('bookings') \
            .where('barber_name', '==', barber_name) \
            .where('date', '==', date_str)
        
        if salon_id:
            booking_query = booking_query.where('salon_id', '==', salon_id)
            
        bookings = booking_query.get()
            
        # Get all booked slots for this date
        booked_slots = [booking.to_dict().get('time_slot') for booking in bookings]
        
        # Generate all possible slots (9 AM to 5 PM, 30-min intervals)
        all_slots = []
        current_time = datetime.strptime("09:00", "%H:%M")
        end_time = datetime.strptime("17:00", "%H:%M")
        
        while current_time < end_time:
            slot = current_time.strftime("%I:%M %p")
            if slot not in booked_slots:
                all_slots.append(slot)
            current_time += timedelta(minutes=30)
            
        return all_slots
        
    except Exception as e:
        logger.error(f"Error getting available slots: {str(e)}")
        return []

def book_slot(booking_data: Dict, salon_id: str = None) -> Dict[str, str]:
    """
    Book a slot for a barber
    
    Args:
        booking_data: Dictionary containing booking information
        salon_id: Salon ID for the booking
            
    Returns:
        Dict with status and message
    """
    if use_mock_database():
        # Mock booking success for testing
        return {
            'status': 'success',
            'message': 'Booking confirmed successfully (mock)',
            'booking_id': f"mock_booking_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        }
    
    if not db:
        logger.error("Database not available. Cannot book slot.")
        return {
            'status': 'error',
            'message': 'Database connection error. Please try again later.'
        }
    
    try:
        # Add salon_id to booking data
        if salon_id:
            booking_data['salon_id'] = salon_id
        
        # Add date if not provided
        if 'date' not in booking_data:
            booking_data['date'] = datetime.now().strftime("%Y-%m-%d")
            
        # Check if slot is available
        available_slots = get_available_slots(
            booking_data['barber_name'], 
            datetime.strptime(booking_data['date'], "%Y-%m-%d"),
            salon_id
        )
        
        if booking_data['time_slot'] not in available_slots:
            return {
                'status': 'error',
                'message': 'This time slot is not available'
            }
            
        # Add the booking
        booking_data['status'] = 'confirmed'
        booking_data['source'] = 'whatsapp'
        booking_data['created_at'] = datetime.now().isoformat()
        
        # Save to database
        doc_ref = db.collection('bookings').add(booking_data)
        booking_data['booking_id'] = doc_ref[1].id
        
        logger.info(f"Saved booking to database: {booking_data}")
        return {
            'status': 'success',
            'message': 'Booking confirmed successfully',
            'booking_id': booking_data['booking_id']
        }
        
    except Exception as e:
        logger.error(f"Error saving booking: {str(e)}")
        return {
            'status': 'error',
            'message': 'Failed to save booking. Please try again.'
        }

def check_barbers_initialized():
    """Check if barbers are properly initialized in Firestore"""
    try:
        barbers_ref = db.collection('barbers')
        barbers = barbers_ref.stream()
        logger.info("Current barbers in database:")
        for barber in barbers:
            data = barber.to_dict()
            logger.info(f"Barber {barber.id}: {data}")
        return True
    except Exception as e:
        logger.error(f"Error checking barbers: {str(e)}")
        return False

def get_salon(salon_id: str) -> Optional[Salon]:
    """Get a specific salon by ID"""
    if use_mock_database():
        salon_data = MOCK_DATABASE["salons"].get(salon_id)
        if salon_data:
            return Salon(**salon_data)
        return None
    
    if not db:
        logger.error("Database not available. Cannot get salon.")
        return None
    
    try:
        doc = db.collection('salons').document(salon_id).get()
        if doc.exists:
            salon_data = doc.to_dict()
            salon_data['id'] = doc.id
            return Salon(**salon_data)
        return None
    except Exception as e:
        logger.error(f"Error getting salon: {str(e)}")
        return None

def get_all_salons() -> List[Salon]:
    """Get all salons from Firestore"""
    if use_mock_database():
        salons = []
        for salon_data in MOCK_DATABASE["salons"].values():
            if salon_data.get("active", True):
                salons.append(Salon(**salon_data))
        return salons
    
    if not db:
        logger.error("Database not available. Cannot get salons.")
        return []
    
    try:
        salons = []
        for doc in db.collection('salons').where('active', '==', True).stream():
            salon_data = doc.to_dict()
            salon_data['id'] = doc.id
            salons.append(Salon(**salon_data))
        return salons
    except Exception as e:
        logger.error(f"Error getting salons: {str(e)}")
        return []

def init_default_data():
    """Initialize default salons, services and barbers for multi-salon setup"""
    if not db:
        logger.error("Firebase is not initialized. Cannot initialize default data.")
        return

    try:
        # Initialize salons first
        salons_ref = db.collection('salons')
        existing_salons = list(salons_ref.stream())
        
        if len(existing_salons) == 0:
            logger.info("No salons found. Initializing multi-salon setup...")
            
            # Create default salons
            default_salons = [
                Salon(
                    id="salon_a",
                    name="Downtown Beauty Salon", 
                    phone=settings.SALON_A_PHONE,
                    address="123 Main Street, Downtown",
                    whatsapp_service_url=settings.SALON_A_WHATSAPP_URL,
                    working_hours={"Monday": "09:00-17:00", "Tuesday": "09:00-17:00", "Wednesday": "09:00-17:00", "Thursday": "09:00-17:00", "Friday": "09:00-17:00", "Saturday": "10:00-16:00"},
                    timezone="UTC",
                    active=True
                ),
                Salon(
                    id="salon_b", 
                    name="Uptown Hair Studio",
                    phone=settings.SALON_B_PHONE,
                    address="456 Oak Avenue, Uptown",
                    whatsapp_service_url=settings.SALON_B_WHATSAPP_URL,
                    working_hours={"Monday": "10:00-18:00", "Tuesday": "10:00-18:00", "Wednesday": "10:00-18:00", "Thursday": "10:00-18:00", "Friday": "10:00-18:00", "Saturday": "09:00-17:00"},
                    timezone="UTC",
                    active=True
                ),
                Salon(
                    id="salon_c",
                    name="Luxury Spa & Salon",
                    phone=settings.SALON_C_PHONE, 
                    address="789 Elm Street, Westside",
                    whatsapp_service_url=settings.SALON_C_WHATSAPP_URL,
                    working_hours={"Tuesday": "09:00-17:00", "Wednesday": "09:00-17:00", "Thursday": "09:00-17:00", "Friday": "09:00-17:00", "Saturday": "10:00-18:00", "Sunday": "10:00-16:00"},
                    timezone="UTC",
                    active=True
                )
            ]
            
            # Initialize salons
            for salon in default_salons:
                doc_ref = salons_ref.document(salon.id)
                doc_ref.set(salon.dict())
                logger.info(f"Initialized salon: {salon.name}")
        else:
            logger.info(f"Found {len(existing_salons)} existing salons")

        # Check if services already exist
        services_ref = db.collection('services')
        existing_services = list(services_ref.stream())
        
        if len(existing_services) == 0:
            logger.info("No services found. Initializing multi-salon services...")
            
            # Create services for each salon
            base_services = [
                {"id": "1", "name": "Hair Cut", "duration": 30, "price": 25.00, "description": "Professional hair cutting and styling"},
                {"id": "2", "name": "Hair Color", "duration": 90, "price": 75.00, "description": "Hair coloring and highlights"},
                {"id": "3", "name": "Manicure", "duration": 45, "price": 30.00, "description": "Professional nail care and manicure"},
                {"id": "4", "name": "Pedicure", "duration": 45, "price": 40.00, "description": "Complete foot care and pedicure"},
                {"id": "5", "name": "Hair Wash & Blow Dry", "duration": 30, "price": 20.00, "description": "Hair wash and professional blow dry"},
                {"id": "6", "name": "Facial Treatment", "duration": 60, "price": 50.00, "description": "Rejuvenating facial treatment"},
                {"id": "7", "name": "Beard Trim", "duration": 20, "price": 15.00, "description": "Professional beard trimming and shaping"},
                {"id": "8", "name": "Eyebrow Threading", "duration": 15, "price": 12.00, "description": "Precise eyebrow shaping and threading"}
            ]
            
            salon_ids = ["salon_a", "salon_b", "salon_c"]
            
            # Create services for each salon
            for salon_id in salon_ids:
                for service_data in base_services:
                    service = Service(
                        id=f"{salon_id}_{service_data['id']}",  # Unique ID per salon
                        salon_id=salon_id,
                        name=service_data["name"],
                        duration=service_data["duration"],
                        price=service_data["price"],
                        description=service_data["description"]
                    )
                    doc_ref = services_ref.document(service.id)
                    doc_ref.set(service.dict())
                    logger.info(f"Initialized service: {service.name} for {salon_id}")
        else:
            logger.info(f"Found {len(existing_services)} existing services")

        # Check if barbers already exist
        barbers_ref = db.collection('barbers')
        existing_barbers = list(barbers_ref.stream())
        
        if len(existing_barbers) == 0:
            logger.info("No barbers found. Initializing multi-salon staff...")
            
            # Create barbers for each salon
            salon_barbers = {
                "salon_a": [
                    {"name": "Maya", "services": ["salon_a_1", "salon_a_2", "salon_a_5", "salon_a_6"], "email": "maya@downtownbeauty.com", "working_days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"], "specialties": ["Hair Coloring", "Facial Treatments"], "experience_years": 6},
                    {"name": "Raj", "services": ["salon_a_1", "salon_a_3", "salon_a_4", "salon_a_7"], "email": "raj@downtownbeauty.com", "working_days": ["Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"], "specialties": ["Men's Grooming", "Nail Care"], "experience_years": 4}
                ],
                "salon_b": [  
                    {"name": "Aisha", "services": ["salon_b_1", "salon_b_2", "salon_b_3", "salon_b_5", "salon_b_8"], "email": "aisha@uptownhair.com", "working_days": ["Monday", "Wednesday", "Thursday", "Friday", "Saturday"], "specialties": ["Hair Styling", "Beauty Treatments"], "experience_years": 8},
                    {"name": "Ravi", "services": ["salon_b_1", "salon_b_7", "salon_b_5"], "email": "ravi@uptownhair.com", "working_days": ["Monday", "Tuesday", "Thursday", "Friday", "Saturday"], "specialties": ["Men's Haircuts", "Beard Styling"], "experience_years": 5}
                ],
                "salon_c": [
                    {"name": "Priya", "services": ["salon_c_3", "salon_c_4", "salon_c_6", "salon_c_8"], "email": "priya@luxuryspa.com", "working_days": ["Tuesday", "Friday", "Saturday", "Sunday"], "specialties": ["Spa Treatments", "Nail Art"], "experience_years": 7},
                    {"name": "Dev", "services": ["salon_c_1", "salon_c_2", "salon_c_5"], "email": "dev@luxuryspa.com", "working_days": ["Wednesday", "Thursday", "Friday", "Saturday", "Sunday"], "specialties": ["Hair Design", "Color Specialist"], "experience_years": 9}
                ]
            }
            
            # Initialize barbers for each salon
            for salon_id, barbers in salon_barbers.items():
                for barber_data in barbers:
                    barber = Barber(
                        name=barber_data["name"],
                        salon_id=salon_id,
                        email=barber_data["email"],
                        services=barber_data["services"],
                        working_days=barber_data["working_days"],
                        specialties=barber_data["specialties"],
                        experience_years=barber_data["experience_years"]
                    )
                    # Use salon_id + name as document ID for uniqueness
                    doc_ref = barbers_ref.document(f"{salon_id}_{barber.name.lower()}")
                    doc_ref.set(barber.dict())
                    logger.info(f"Initialized barber: {barber.name} for {salon_id}")
        else:
            logger.info(f"Found {len(existing_barbers)} existing barbers")
            
        logger.info("Multi-salon data initialization complete")
        
    except Exception as e:
        logger.error(f"Error initializing multi-salon data: {str(e)}")

def get_all_services(salon_id: str = None):
    """Get all services from Firestore, optionally filtered by salon"""
    if use_mock_database():
        services = []
        for service_data in MOCK_DATABASE["services"].values():
            if not salon_id or service_data.get("salon_id") == salon_id:
                services.append(Service(**service_data))
        return services
    
    if not db:
        logger.error("Database not available. Cannot get services.")
        return []
    
    try:
        query = db.collection('services')
        if salon_id:
            query = query.where('salon_id', '==', salon_id)
        
        services = []
        for doc in query.stream():
            service_data = doc.to_dict()
            service_data['id'] = doc.id
            services.append(Service(**service_data))
        return services
    except Exception as e:
        logger.error(f"Error getting services: {str(e)}")
        return []

def get_service(service_id: str, salon_id: str = None):
    """Get a specific service by ID, optionally filtered by salon"""
    if use_mock_database():
        # If salon_id is provided, construct the full service ID
        if salon_id and not service_id.startswith(salon_id):
            full_service_id = f"{salon_id}_{service_id}"
        else:
            full_service_id = service_id
            
        service_data = MOCK_DATABASE["services"].get(full_service_id)
        if service_data:
            return Service(**service_data)
        return None
    
    if not db:
        logger.error("Database not available. Cannot get service.")
        return None
    
    try:
        # If salon_id is provided, construct the full service ID
        if salon_id and not service_id.startswith(salon_id):
            full_service_id = f"{salon_id}_{service_id}"
        else:
            full_service_id = service_id
            
        doc = db.collection('services').document(full_service_id).get()
        if doc.exists:
            service_data = doc.to_dict()
            service_data['id'] = doc.id
            return Service(**service_data)
        return None
    except Exception as e:
        logger.error(f"Error getting service: {str(e)}")
        return None

def get_all_barbers(salon_id: str = None):
    """Get all barbers from Firestore, optionally filtered by salon"""
    if use_mock_database():
        barbers = []
        for barber_data in MOCK_DATABASE["barbers"].values():
            if not salon_id or barber_data.get("salon_id") == salon_id:
                barbers.append(Barber(**barber_data))
        return barbers
    
    if not db:
        logger.error("Database not available. Cannot get barbers.")
        return []
    
    try:
        query = db.collection('barbers')
        if salon_id:
            query = query.where('salon_id', '==', salon_id)
            
        barbers = []
        for doc in query.stream():
            barber_data = doc.to_dict()
            barbers.append(Barber(**barber_data))
        return barbers
    except Exception as e:
        logger.error(f"Error getting barbers: {str(e)}")
        return []

def get_barber(email: str, salon_id: str = None):
    """Get a specific barber by email, optionally filtered by salon"""
    if not db:
        logger.error("Database not available. Cannot get barber.")
        return None
    
    try:
        query = db.collection('barbers').where('email', '==', email)
        if salon_id:
            query = query.where('salon_id', '==', salon_id)
            
        barbers = query.get()
        for doc in barbers:
            barber_data = doc.to_dict()
            return Barber(**barber_data)
        return None
    except Exception as e:
        logger.error(f"Error getting barber: {str(e)}")
        return None

def get_barbers_for_service(service_id: str, salon_id: str = None):
    """Get all barbers that provide a specific service, optionally filtered by salon"""
    if use_mock_database():
        barbers = []
        # If salon_id is provided, construct the full service ID
        if salon_id and not service_id.startswith(salon_id):
            full_service_id = f"{salon_id}_{service_id}"
        else:
            full_service_id = service_id
            
        for barber_data in MOCK_DATABASE["barbers"].values():
            if full_service_id in barber_data.get("services", []):
                if not salon_id or barber_data.get("salon_id") == salon_id:
                    barbers.append(Barber(**barber_data))
        return barbers
    
    if not db:
        logger.error("Database not available. Cannot get barbers for service.")
        return []
    
    try:
        logger.info(f"Finding barbers for service ID: {service_id} in salon: {salon_id}")
        
        # If salon_id is provided, construct the full service ID
        if salon_id and not service_id.startswith(salon_id):
            full_service_id = f"{salon_id}_{service_id}"
        else:
            full_service_id = service_id
        
        query = db.collection('barbers').where('services', 'array_contains', full_service_id)
        if salon_id:
            query = query.where('salon_id', '==', salon_id)
            
        docs = query.get()
        logger.info(f"Found {len(list(docs))} barbers")
        
        barbers = []
        for doc in docs:
            barber_data = doc.to_dict()
            logger.info(f"Processing barber: {barber_data}")
            barbers.append(Barber(**barber_data))
        return barbers
    except Exception as e:
        logger.error(f"Error getting barbers for service: {str(e)}")
        return [] 