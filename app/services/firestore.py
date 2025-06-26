from app.services.firestore_simple import (
    init_default_data,
    get_all_services,
    get_all_barbers,
    get_service,
    get_barbers_for_service,
    get_available_slots,
    book_slot,
    is_firebase_connected,
    get_firebase_client,
    get_all_bookings
)

# Re-export all functions from firestore_simple for backward compatibility
__all__ = [
    'init_default_data',
    'get_all_services', 
    'get_all_barbers',
    'get_service',
    'get_barbers_for_service',
    'get_available_slots',
    'book_slot',
    'is_firebase_connected',
    'get_firebase_client',
    'get_all_bookings'
] 