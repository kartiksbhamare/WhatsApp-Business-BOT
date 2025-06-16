from typing import Dict, Optional, List
from pydantic import BaseModel

class Barber(BaseModel):
    name: str
    email: str
    services: List[str] = []  # List of service IDs this barber can perform
    working_days: List[str] = []  # Days of the week this barber works
    specialties: List[str] = []  # Special skills/areas of expertise
    experience_years: int = 0  # Years of experience
    availability: Dict[str, List[str]] = {}  # Day of week -> list of time slots

class Service(BaseModel):
    id: str
    name: str
    duration: int  # Duration in minutes
    price: float
    description: Optional[str] = None 