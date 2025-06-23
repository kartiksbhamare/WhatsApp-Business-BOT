from firebase_admin import credentials, firestore, initialize_app
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Any
import os
import json
from app.config import get_settings
from app.models.services import Service, Barber, Salon, Booking
import logging
from google.cloud import firestore
from google.auth import default

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

# Initialize the database client
def get_firestore_client():
    """Get Firestore client, initializing if needed"""
    try:
        # Use project ID from environment
        project_id = settings.FIREBASE_PROJECT_ID
        if not project_id:
            logger.error("No Firebase project ID found in environment variables")
            return None
        
        logger.info(f"Initializing Firestore with project ID: {project_id}")
        
        # Try to get default credentials (works if gcloud is configured)
        try:
            credentials, _ = default()
            return firestore.Client(project=project_id, credentials=credentials)
        except Exception as cred_error:
            logger.warning(f"Default credentials failed: {cred_error}")
            # Try without explicit credentials (uses application default)
            return firestore.Client(project=project_id)
            
    except Exception as e:
        logger.error(f"Error initializing Firestore client: {str(e)}")
        logger.info("💡 Make sure Firebase project ID is set in environment variables")
        return None

db = get_firestore_client()

# Global fallback storage
LOCAL_DB_FILE = "local_firebase_data.json"
local_db = {
    "salons": {},
    "services": {},
    "barbers": {},
    "bookings": {}
}

def load_local_db():
    """Load local database from file"""
    global local_db
    try:
        if os.path.exists(LOCAL_DB_FILE):
            with open(LOCAL_DB_FILE, 'r') as f:
                local_db = json.load(f)
                logger.info("📂 Loaded local database from file")
    except Exception as e:
        logger.error(f"Error loading local database: {e}")

def save_local_db():
    """Save local database to file"""
    try:
        with open(LOCAL_DB_FILE, 'w') as f:
            json.dump(local_db, f, indent=2)
            logger.info("💾 Saved local database to file")
    except Exception as e:
        logger.error(f"Error saving local database: {e}")

# Load local database on import
load_local_db()

def use_local_storage():
    """Check if we should use local storage instead of Firebase"""
    return db is None

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

def get_salon(salon_id: str) -> Dict[str, Any]:
    """Get salon by ID"""
    if use_local_storage():
        # Use local storage
        salon_data = local_db.get("salons", {}).get(salon_id)
        if salon_data:
            return salon_data
        else:
            logger.warning(f"Salon {salon_id} not found in local storage")
            return None
    else:
        # Use Firebase (original code)
        try:
            salon_ref = db.collection('salons').document(salon_id)
            salon_doc = salon_ref.get()
            
            if salon_doc.exists:
                return salon_doc.to_dict()
            else:
                logger.warning(f"Salon {salon_id} not found in Firebase")
                return None
                
        except Exception as e:
            logger.error(f"Error getting salon {salon_id} from Firebase: {str(e)}")
            return None

def get_salons() -> List[Dict[str, Any]]:
    """Get all salons"""
    if use_local_storage():
        # Use local storage
        salon_data = local_db.get("salons", {})
        return list(salon_data.values())
    else:
        # Use Firebase (original code)
        try:
            salons_ref = db.collection('salons')
            salons = salons_ref.stream()
            
            salon_list = []
            for salon in salons:
                salon_data = salon.to_dict()
                salon_list.append(salon_data)
            
            return salon_list
            
        except Exception as e:
            logger.error(f"Error getting salons from Firebase: {str(e)}")
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
    """Get all services from Firestore or local storage, optionally filtered by salon"""
    if use_local_storage():
        # Use local storage
        salon_data = local_db.get("salons", {})
        if salon_id and salon_id in salon_data:
            services = salon_data[salon_id].get("services", [])
            # Convert to simple objects with required attributes
            service_objects = []
            for i, service in enumerate(services):
                service_obj = type('Service', (), {
                    'id': f"{salon_id}_{i+1}",
                    'name': service['name'],
                    'duration': service['duration'],
                    'price': service['price'],
                    'description': f"{service['name']} service"
                })()
                service_objects.append(service_obj)
            return service_objects
        elif not salon_id:
            # Return all services from all salons
            all_services = []
            for s_id, salon in salon_data.items():
                services = salon.get("services", [])
                for i, service in enumerate(services):
                    service_obj = type('Service', (), {
                        'id': f"{s_id}_{i+1}",
                        'name': service['name'],
                        'duration': service['duration'],
                        'price': service['price'],
                        'description': f"{service['name']} service"
                    })()
                    all_services.append(service_obj)
            return all_services
        return []
    else:
        # Use Firebase (original code)
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

def initialize_salon_data():
    """Initialize salon data in Firestore or local storage"""
    if not use_local_storage() and db:
        # Use Firebase
        try:
            salon_data = [
                {
                    "id": "salon_a",
                    "name": "Downtown Beauty Salon", 
                    "address": "123 Downtown St, City Center",
                    "phone": "919307748525",
                    "email": "downtown@beauty.com",
                    "services": [
                        {"name": "Haircut", "duration": 30, "price": 25.0},
                        {"name": "Hair Wash", "duration": 15, "price": 10.0},
                        {"name": "Styling", "duration": 45, "price": 35.0}
                    ],
                    "barbers": [
                        {"name": "Alex", "specialties": ["Haircut", "Styling"]},
                        {"name": "Maria", "specialties": ["Hair Wash", "Styling"]}
                    ],
                    "working_hours": {
                        "monday": "09:00-18:00",
                        "tuesday": "09:00-18:00", 
                        "wednesday": "09:00-18:00",
                        "thursday": "09:00-18:00",
                        "friday": "09:00-18:00",
                        "saturday": "10:00-16:00",
                        "sunday": "Closed"
                    }
                },
                {
                    "id": "salon_b", 
                    "name": "Uptown Hair Studio",
                    "address": "456 Uptown Ave, Fashion District",
                    "phone": "919307748525",
                    "email": "uptown@hairstudio.com",
                    "services": [
                        {"name": "Premium Cut", "duration": 60, "price": 50.0},
                        {"name": "Color Treatment", "duration": 120, "price": 80.0},
                        {"name": "Deep Conditioning", "duration": 45, "price": 40.0}
                    ],
                    "barbers": [
                        {"name": "Sophie", "specialties": ["Premium Cut", "Color Treatment"]},
                        {"name": "James", "specialties": ["Premium Cut", "Deep Conditioning"]}
                    ],
                    "working_hours": {
                        "monday": "10:00-19:00",
                        "tuesday": "10:00-19:00",
                        "wednesday": "10:00-19:00", 
                        "thursday": "10:00-19:00",
                        "friday": "10:00-19:00",
                        "saturday": "09:00-17:00",
                        "sunday": "11:00-16:00"
                    }
                },
                {
                    "id": "salon_c",
                    "name": "Luxury Spa & Salon",
                    "address": "789 Luxury Blvd, Premium District", 
                    "phone": "919307748525",
                    "email": "luxury@spa.com",
                    "services": [
                        {"name": "Luxury Haircut", "duration": 90, "price": 100.0},
                        {"name": "Spa Treatment", "duration": 180, "price": 200.0},
                        {"name": "Facial & Hair", "duration": 120, "price": 150.0}
                    ],
                    "barbers": [
                        {"name": "Isabella", "specialties": ["Luxury Haircut", "Spa Treatment"]},
                        {"name": "Michael", "specialties": ["Luxury Haircut", "Facial & Hair"]}
                    ],
                    "working_hours": {
                        "monday": "08:00-20:00",
                        "tuesday": "08:00-20:00",
                        "wednesday": "08:00-20:00",
                        "thursday": "08:00-20:00", 
                        "friday": "08:00-20:00",
                        "saturday": "09:00-18:00",
                        "sunday": "10:00-17:00"
                    }
                }
            ]
            
            # Initialize each salon in Firebase
            for salon in salon_data:
                salon_ref = db.collection('salons').document(salon['id'])
                salon_ref.set(salon)
                logger.info(f"✅ Initialized salon in Firebase: {salon['name']} ({salon['id']})")
            
            logger.info("🎉 All salon data initialized successfully in Firebase!")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing salon data in Firebase: {str(e)}")
            return False
    else:
        # Use local storage fallback
        try:
            global local_db
            salon_data = {
                "salon_a": {
                    "id": "salon_a",
                    "name": "Downtown Beauty Salon", 
                    "address": "123 Downtown St, City Center",
                    "phone": "919307748525",
                    "email": "downtown@beauty.com",
                    "services": [
                        {"name": "Haircut", "duration": 30, "price": 25.0},
                        {"name": "Hair Wash", "duration": 15, "price": 10.0},
                        {"name": "Styling", "duration": 45, "price": 35.0}
                    ],
                    "barbers": [
                        {"name": "Alex", "specialties": ["Haircut", "Styling"]},
                        {"name": "Maria", "specialties": ["Hair Wash", "Styling"]}
                    ],
                    "working_hours": {
                        "monday": "09:00-18:00",
                        "tuesday": "09:00-18:00", 
                        "wednesday": "09:00-18:00",
                        "thursday": "09:00-18:00",
                        "friday": "09:00-18:00",
                        "saturday": "10:00-16:00",
                        "sunday": "Closed"
                    }
                },
                "salon_b": {
                    "id": "salon_b", 
                    "name": "Uptown Hair Studio",
                    "address": "456 Uptown Ave, Fashion District",
                    "phone": "919307748525",
                    "email": "uptown@hairstudio.com",
                    "services": [
                        {"name": "Premium Cut", "duration": 60, "price": 50.0},
                        {"name": "Color Treatment", "duration": 120, "price": 80.0},
                        {"name": "Deep Conditioning", "duration": 45, "price": 40.0}
                    ],
                    "barbers": [
                        {"name": "Sophie", "specialties": ["Premium Cut", "Color Treatment"]},
                        {"name": "James", "specialties": ["Premium Cut", "Deep Conditioning"]}
                    ],
                    "working_hours": {
                        "monday": "10:00-19:00",
                        "tuesday": "10:00-19:00",
                        "wednesday": "10:00-19:00", 
                        "thursday": "10:00-19:00",
                        "friday": "10:00-19:00",
                        "saturday": "09:00-17:00",
                        "sunday": "11:00-16:00"
                    }
                },
                "salon_c": {
                    "id": "salon_c",
                    "name": "Luxury Spa & Salon",
                    "address": "789 Luxury Blvd, Premium District", 
                    "phone": "919307748525",
                    "email": "luxury@spa.com",
                    "services": [
                        {"name": "Luxury Haircut", "duration": 90, "price": 100.0},
                        {"name": "Spa Treatment", "duration": 180, "price": 200.0},
                        {"name": "Facial & Hair", "duration": 120, "price": 150.0}
                    ],
                    "barbers": [
                        {"name": "Isabella", "specialties": ["Luxury Haircut", "Spa Treatment"]},
                        {"name": "Michael", "specialties": ["Luxury Haircut", "Facial & Hair"]}
                    ],
                    "working_hours": {
                        "monday": "08:00-20:00",
                        "tuesday": "08:00-20:00",
                        "wednesday": "08:00-20:00",
                        "thursday": "08:00-20:00", 
                        "friday": "08:00-20:00",
                        "saturday": "09:00-18:00",
                        "sunday": "10:00-17:00"
                    }
                }
            }
            
            local_db["salons"] = salon_data
            save_local_db()
            
            logger.info("🎉 All salon data initialized successfully in local storage!")
            logger.info("📝 Note: Using local storage as Firebase backup. Data will migrate when Firebase is connected.")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing salon data in local storage: {str(e)}")
            return False 