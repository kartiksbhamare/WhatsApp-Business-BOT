from firebase_admin import credentials, firestore, initialize_app
from datetime import datetime, timedelta
from typing import Dict, Optional, List
import os
import json
from app.config import get_settings
from app.models.services import Service, Barber
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

def get_available_slots(barber_name: str, date: datetime = None) -> List[str]:
    """
    Get available slots for a barber on a specific date
    
    Args:
        barber_name: Name of the barber
        date: Date to check (defaults to today)
        
    Returns:
        List of available time slots
    """
    if not db:
        logger.error("Database not available. Cannot get available slots.")
        return []
    
    if not date:
        date = datetime.now()
    
    date_str = date.strftime("%Y-%m-%d")
    
    try:
        # Get barber's document
        barber_ref = db.collection('barbers').document(barber_name.lower())
        barber_doc = barber_ref.get()
        
        if not barber_doc.exists:
            logger.error(f"Barber {barber_name} not found")
            return []
            
        # Get bookings for this barber on this date
        bookings = db.collection('bookings') \
            .where('barber_name', '==', barber_name) \
            .where('date', '==', date_str) \
            .get()
            
        # Get all booked slots for this date
        booked_slots = [booking.get('time_slot') for booking in bookings]
        
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

def book_slot(booking_data: Dict) -> Dict[str, str]:
    """
    Book a slot for a barber
    
    Args:
        booking_data: Dictionary containing:
            - barber_name: Name of the barber
            - time_slot: Time slot to book
            - date: Date of booking
            - service_name: Service being booked
            - phone: Customer's phone
            
    Returns:
        Dict with status and message
    """
    if not db:
        logger.error("Database not available. Cannot book slot.")
        return {
            'status': 'error',
            'message': 'Database connection error. Please try again later.'
        }
    
    try:
        # Add date if not provided
        if 'date' not in booking_data:
            booking_data['date'] = datetime.now().strftime("%Y-%m-%d")
            
        # Check if slot is available
        available_slots = get_available_slots(
            booking_data['barber_name'], 
            datetime.strptime(booking_data['date'], "%Y-%m-%d")
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

def init_default_data():
    """Initialize default services and barbers for the salon"""
    if not db:
        logger.error("Firebase is not initialized. Cannot initialize default data.")
        return

    try:
        # Check if services already exist
        services_ref = db.collection('services')
        existing_services = list(services_ref.stream())
        
        if len(existing_services) == 0:
            logger.info("No services found. Initializing salon services...")
            
            # Professional salon services
            default_services = [
                Service(
                    id="1",
                    name="Haircut",
                    duration=30,
                    price=25.00,
                    description="Professional haircut and styling"
                ),
                Service(
                    id="2",
                    name="Hair Color",
                    duration=90,
                    price=75.00,
                    description="Full hair coloring service"
                ),
                Service(
                    id="3",
                    name="Manicure",
                    duration=45,
                    price=35.00,
                    description="Professional nail care and manicure"
                ),
                Service(
                    id="4",
                    name="Pedicure",
                    duration=45,
                    price=40.00,
                    description="Complete foot care and pedicure"
                ),
                Service(
                    id="5",
                    name="Hair Wash & Blow Dry",
                    duration=30,
                    price=20.00,
                    description="Hair wash and professional blow dry"
                ),
                Service(
                    id="6",
                    name="Facial Treatment",
                    duration=60,
                    price=50.00,
                    description="Rejuvenating facial treatment"
                ),
                Service(
                    id="7",
                    name="Beard Trim",
                    duration=20,
                    price=15.00,
                    description="Professional beard trimming and shaping"
                ),
                Service(
                    id="8",
                    name="Eyebrow Threading",
                    duration=15,
                    price=12.00,
                    description="Precise eyebrow shaping and threading"
                )
            ]

            # Initialize services
            for service in default_services:
                doc_ref = services_ref.document(service.id)
                doc_ref.set(service.dict())
                logger.info(f"Initialized service: {service.name}")
        else:
            logger.info(f"Found {len(existing_services)} existing services")

        # Check if barbers already exist
        barbers_ref = db.collection('barbers')
        existing_barbers = list(barbers_ref.stream())
        
        if len(existing_barbers) == 0:
            logger.info("No barbers found. Initializing salon staff...")
            
            # Professional salon staff (single salon)
            salon_barbers = [
                {
                    "name": "Maya",
                    "services": ["1", "2", "5", "6"],  # Haircut, Hair Color, Wash & Blow Dry, Facial
                    "email": "maya@yoursalon.com",
                    "working_days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
                    "specialties": ["Hair Coloring", "Facial Treatments"],
                    "experience_years": 6
                },
                {
                    "name": "Raj",
                    "services": ["1", "3", "4", "7"],  # Haircut, Manicure, Pedicure, Beard Trim
                    "email": "raj@yoursalon.com",
                    "working_days": ["Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"],
                    "specialties": ["Men's Grooming", "Nail Care"],
                    "experience_years": 4
                },
                {
                    "name": "Aisha",
                    "services": ["1", "2", "3", "4", "5", "8"],  # All services except Facial and Beard
                    "email": "aisha@yoursalon.com",
                    "working_days": ["Monday", "Wednesday", "Thursday", "Friday", "Saturday"],
                    "specialties": ["Hair Styling", "Beauty Treatments"],
                    "experience_years": 8
                },
                {
                    "name": "Ravi",
                    "services": ["1", "7", "5"],  # Haircut, Beard Trim, Hair Wash
                    "email": "ravi@yoursalon.com",
                    "working_days": ["Monday", "Tuesday", "Thursday", "Friday", "Saturday"],
                    "specialties": ["Men's Haircuts", "Beard Styling"],
                    "experience_years": 5
                },
                {
                    "name": "Priya",
                    "services": ["3", "4", "6", "8"],  # Manicure, Pedicure, Facial, Eyebrow Threading
                    "email": "priya@yoursalon.com",
                    "working_days": ["Monday", "Tuesday", "Friday", "Saturday", "Sunday"],
                    "specialties": ["Beauty Treatments", "Nail Art"],
                    "experience_years": 3
                }
            ]

            # Initialize barbers
            for barber in salon_barbers:
                # Use lowercase name as document ID for consistency
                doc_ref = barbers_ref.document(barber['name'].lower())
                doc_ref.set(barber)
                logger.info(f"Initialized barber: {barber['name']}")
        else:
            logger.info(f"Found {len(existing_barbers)} existing barbers")
            
        logger.info("Single salon data initialization complete")
        
    except Exception as e:
        logger.error(f"Error initializing salon data: {str(e)}")

def get_all_services():
    """Get all services from Firestore"""
    if not db:
        logger.error("Database not available. Cannot get services.")
        return []
    
    try:
        services = []
        for doc in db.collection('services').stream():
            service_data = doc.to_dict()
            service_data['id'] = doc.id
            services.append(Service(**service_data))
        return services
    except Exception as e:
        logger.error(f"Error getting services: {str(e)}")
        return []

def get_service(service_id: str):
    """Get a specific service by ID"""
    if not db:
        logger.error("Database not available. Cannot get service.")
        return None
    
    try:
        doc = db.collection('services').document(service_id).get()
        if doc.exists:
            service_data = doc.to_dict()
            service_data['id'] = doc.id
            return Service(**service_data)
        return None
    except Exception as e:
        logger.error(f"Error getting service: {str(e)}")
        return None

def get_all_barbers():
    """Get all barbers from Firestore"""
    if not db:
        logger.error("Database not available. Cannot get barbers.")
        return []
    
    try:
        barbers = []
        for doc in db.collection('barbers').stream():
            barber_data = doc.to_dict()
            barber_data['name'] = doc.id
            barbers.append(Barber(**barber_data))
        return barbers
    except Exception as e:
        logger.error(f"Error getting barbers: {str(e)}")
        return []

def get_barber(email: str):
    """Get a specific barber by email"""
    if not db:
        logger.error("Database not available. Cannot get barber.")
        return None
    
    try:
        barbers = db.collection('barbers').where('email', '==', email).get()
        for doc in barbers:
            barber_data = doc.to_dict()
            barber_data['name'] = doc.id
            return Barber(**barber_data)
        return None
    except Exception as e:
        logger.error(f"Error getting barber: {str(e)}")
        return None

def get_barbers_for_service(service_id: str):
    """Get all barbers that provide a specific service"""
    if not db:
        logger.error("Database not available. Cannot get barbers for service.")
        return []
    
    try:
        logger.info(f"Finding barbers for service ID: {service_id}")
        barbers = []
        docs = db.collection('barbers').where('services', 'array_contains', service_id).get()
        logger.info(f"Found {len(list(docs))} barbers")
        for doc in docs:
            barber_data = doc.to_dict()
            barber_data['name'] = doc.id
            logger.info(f"Processing barber: {barber_data}")
            barbers.append(Barber(**barber_data))
        return barbers
    except Exception as e:
        logger.error(f"Error getting barbers for service: {str(e)}")
        return [] 