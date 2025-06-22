from typing import Dict, Optional, List
from pydantic import BaseModel

class Salon(BaseModel):
    """Salon model for multi-salon support"""
    id: str
    name: str
    phone: str  # WhatsApp phone number for this salon
    address: str
    whatsapp_service_url: str  # URL of the WhatsApp service for this salon
    working_hours: Dict[str, str] = {}  # Day -> "09:00-17:00"
    timezone: str = "UTC"
    active: bool = True

class Barber(BaseModel):
    name: str
    salon_id: str  # NEW FIELD - which salon this barber belongs to
    email: str
    services: List[str] = []  # List of service IDs this barber can perform
    working_days: List[str] = []  # Days of the week this barber works
    specialties: List[str] = []  # Special skills/areas of expertise
    experience_years: int = 0  # Years of experience
    availability: Dict[str, List[str]] = {}  # Day of week -> list of time slots

class Service(BaseModel):
    id: str
    salon_id: str  # NEW FIELD - which salon this service belongs to
    name: str
    duration: int  # Duration in minutes
    price: float
    description: Optional[str] = None

class Booking(BaseModel):
    """Booking model for appointments"""
    id: Optional[str] = None
    salon_id: str  # NEW FIELD - which salon this booking is for
    service_id: str
    service_name: str
    barber_name: str
    time_slot: str
    date: str
    phone: str
    contact_name: str
    status: str = "confirmed"
    source: str = "whatsapp"
    created_at: Optional[str] = None 