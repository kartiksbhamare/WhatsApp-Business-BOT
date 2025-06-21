from fastapi import FastAPI, Request, HTTPException, Form, Response
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Optional
from datetime import datetime
import json
import logging
import re

from app.services.firestore import (
    init_default_data,
    get_all_services,
    get_all_barbers,
    get_service,
    get_barber,
    get_barbers_for_service,
    get_available_slots,
    book_slot
)
from app.services.whatsapp import send_whatsapp_message, check_whatsapp_service_health
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

app = FastAPI(
    title="Smart WhatsApp Booking Bot",
    description="A WhatsApp-based booking system for salons using FastAPI, Firebase and WhatsApp Web.js",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory session storage
sessions = {}

def get_session_data(phone: str) -> Dict:
    """Get or create session data for a phone number"""
    if phone not in sessions:
        sessions[phone] = {
            "step": "service",
            "service": None,
            "barber": None,
            "time_slot": None
        }
    return sessions[phone]

def clear_session(phone: str):
    """Clear session data for a phone number"""
    if phone in sessions:
        del sessions[phone]

@app.on_event("startup")
async def startup_event():
    """Initialize the database with default data if empty"""
    from app.config_check import run_config_check
    
    # Check configuration
    logger.info("Running configuration check...")
    config_ok = run_config_check()
    if not config_ok:
        logger.error("Configuration check failed! Please check your environment variables.")
    else:
        logger.info("Configuration check passed.")
    
    # Check WhatsApp Web service
    logger.info("Checking WhatsApp Web service...")
    if check_whatsapp_service_health():
        logger.info("✅ WhatsApp Web service is ready!")
    else:
        logger.warning("⚠️ WhatsApp Web service is not ready. Please make sure to start the WhatsApp Web service first.")
    
    # Initialize database
    init_default_data()

@app.get("/")
async def root():
    """Root endpoint with basic info"""
    whatsapp_status = "ready" if check_whatsapp_service_health() else "not ready"
    return {
        "service": "Smart WhatsApp Booking Bot",
        "status": "running", 
        "message": "Smart WhatsApp Booking Bot is running",
        "whatsapp_service": whatsapp_status,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/health")
async def health_check():
    """Health check endpoint for Railway deployment"""
    try:
        whatsapp_healthy = check_whatsapp_service_health()
        
        # Check database connection
        db_healthy = True
        try:
            # Try to access Firebase
            services = get_all_services()
            db_healthy = True
        except Exception as db_error:
            logger.error(f"Database health check failed: {db_error}")
            db_healthy = False
        
        # Be more lenient - consider healthy if FastAPI is running, even if WhatsApp service is down
        overall_status = "healthy" if db_healthy else "degraded"
        
        health_data = {
            "status": overall_status,
            "timestamp": datetime.now().isoformat(),
            "service": "Smart WhatsApp Booking Bot",
            "version": "1.0.0",
            "components": {
                "whatsapp_service": "healthy" if whatsapp_healthy else "unhealthy",
                "database": "healthy" if db_healthy else "unhealthy",
                "api": "healthy"
            },
            "message": "FastAPI backend is running. WhatsApp service may still be initializing."
        }
        
        # Always return 200 if FastAPI is running - don't fail health check for WhatsApp service
        return health_data
        
    except Exception as e:
        logger.error(f"Health check error: {e}")
        raise HTTPException(status_code=503, detail={
            "status": "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        })

@app.get("/api/services")
async def get_services():
    """Get all available services"""
    services = get_all_services()
    return {"services": [{"id": s.id, "name": s.name, "price": s.price, "duration": s.duration, "description": s.description} for s in services]}

@app.get("/api/barbers")
async def get_barbers():
    """Get all available barbers"""
    barbers = get_all_barbers()
    return {"barbers": [{"name": b.name, "email": b.email, "services": b.services, "working_days": b.working_days} for b in barbers]}

@app.get("/api/barbers/service/{service_id}")
async def get_barbers_by_service(service_id: str):
    """Get barbers that provide a specific service"""
    barbers = get_barbers_for_service(service_id)
    return {"service_id": service_id, "barbers": [{"name": b.name, "email": b.email, "working_days": b.working_days} for b in barbers]}

@app.get("/api/slots/{barber_name}")
async def get_barber_slots(barber_name: str):
    """Get available slots for a barber"""
    slots = get_available_slots(barber_name)
    return {"barber": barber_name, "available_slots": slots}

@app.post("/api/initialize")
async def initialize_database():
    """Initialize database with default data"""
    try:
        init_default_data()
        return {"status": "success", "message": "Database initialized successfully"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/api/cleanup")
async def cleanup_database():
    """Clean up old salon data and reset for single salon"""
    try:
        from app.services.firestore import db
        if not db:
            return {"error": "Database not available"}
        
        # COMPLETE CLEANUP - Remove ALL existing data first
        logger.info("Starting complete database cleanup...")
        
        # Remove ALL old barbers
        barbers_ref = db.collection('barbers')
        barbers = barbers_ref.stream()
        barber_count = 0
        for barber in barbers:
            barber.reference.delete()
            barber_count += 1
            logger.info(f"Removed barber: {barber.id}")
        
        # Remove ALL old services 
        services_ref = db.collection('services')
        services = services_ref.stream()
        service_count = 0
        for service in services:
            service.reference.delete() 
            service_count += 1
            logger.info(f"Removed service: {service.id}")
        
        # Remove any salon table if it exists
        try:
            salons = db.collection('salons').stream()
            salon_count = 0
            for salon in salons:
                salon.reference.delete()
                salon_count += 1
                logger.info(f"Removed salon document: {salon.id}")
        except:
            salon_count = 0
        
        # Remove any old bookings to start fresh (optional - comment out if you want to keep)
        bookings_ref = db.collection('bookings')
        bookings = bookings_ref.stream()
        booking_count = 0
        for booking in bookings:
            booking.reference.delete()
            booking_count += 1
            logger.info(f"Removed old booking: {booking.id}")
        
        # Re-initialize with clean single salon data
        init_default_data()
        
        return {
            "status": "success", 
            "message": f"Complete cleanup done. Removed {barber_count} barbers, {service_count} services, {salon_count} salon docs, {booking_count} bookings. Fresh single salon initialized.",
            "cleaned": {
                "barbers": barber_count,
                "services": service_count, 
                "salons": salon_count,
                "bookings": booking_count
            }
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/api/bookings")
async def get_all_bookings():
    """Get all bookings from the database"""
    try:
        from app.services.firestore import db
        if not db:
            return {"error": "Database not available"}
        
        bookings = []
        for doc in db.collection('bookings').stream():
            booking_data = doc.to_dict()
            booking_data['id'] = doc.id
            bookings.append(booking_data)
        
        return {"bookings": bookings, "total": len(bookings)}
    except Exception as e:
        return {"error": str(e)}

@app.post("/webhook/whatsapp")
async def whatsapp_webhook(request: Request):
    """Webhook endpoint for WhatsApp Web.js messages"""
    try:
        logger.info("Received WhatsApp Web webhook request")
        
        # Get JSON data from WhatsApp Web service
        data = await request.json()
        logger.info(f"WhatsApp data: {data}")
        
        message = data.get("body", "").lower().strip()
        phone = data.get("from", "").replace("@c.us", "").replace("@g.us", "")
        
        # Skip group messages
        if data.get("isGroupMsg", False) or "@g.us" in data.get("from", ""):
            logger.info("Skipping group message")
            return {"reply": None}
        
        if not message or not phone:
            logger.error("Missing message or phone in WhatsApp webhook")
            return {"error": "Missing required data"}
            
        logger.info(f"Processing message: '{message}' from phone: {phone}")
        
        # Get session data
        session = get_session_data(phone)
        logger.info(f"Session state: {session}")
        
        reply_message = ""
        
        try:
            # Handle message based on session state
            if message in ["hi", "hello", "start", "restart"]:
                if message in ["restart", "start"]:
                    clear_session(phone)
                    session = get_session_data(phone)
                services = get_all_services()
                service_list = "\n".join([f"{s.id}. {s.name} (${s.price}, {s.duration} mins)" for s in services])
                reply_message = f"Welcome to our Salon! Here are our services:\n\n{service_list}\n\nPlease enter the number of the service you'd like to book."
            
            elif session["step"] == "service" and message.isdigit():
                service = get_service(message)
                if service:
                    barbers = get_barbers_for_service(service.id)
                    if not barbers:
                        reply_message = "Sorry, no barbers are currently available for this service."
                    else:
                        session["service"] = service.id
                        session["step"] = "barber"
                        barber_list = "\n".join([f"{i+1}. {b.name}" for i, b in enumerate(barbers)])
                        reply_message = f"You've selected {service.name}. Please choose your preferred stylist:\n\n{barber_list}"
                else:
                    services = get_all_services()
                    service_list = "\n".join([f"{s.id}. {s.name} (${s.price}, {s.duration} mins)" for s in services])
                    reply_message = f"Invalid service number. Please choose from:\n\n{service_list}"
                
            elif session["step"] == "barber" and message.isdigit():
                try:
                    barbers = get_barbers_for_service(session["service"])
                    selected_barber = barbers[int(message) - 1]
                    session["barber"] = selected_barber.name
                    session["step"] = "time"
                    
                    slots = get_available_slots(selected_barber.name)
                    if not slots:
                        reply_message = "Sorry, no available slots found for today. Please try again tomorrow."
                        clear_session(phone)
                    else:
                        slot_list = "\n".join([f"{i+1}. {slot}" for i, slot in enumerate(slots)])
                        reply_message = f"Please choose your preferred time:\n\n{slot_list}"
                except (IndexError, ValueError):
                    reply_message = "Invalid selection. Please choose a valid number."
                except Exception as e:
                    logger.error(f"Error getting slots: {str(e)}")
                    reply_message = "Sorry, there was an error. Please try again."
                    clear_session(phone)
                
            elif session["step"] == "time" and message.isdigit():
                try:
                    slots = get_available_slots(session["barber"])
                    selected_time = slots[int(message) - 1]
                    
                    service = get_service(session["service"])
                    booking_data = {
                        "service_id": service.id,
                        "service_name": service.name,
                        "barber_name": session["barber"],
                        "time_slot": selected_time,
                        "phone": phone,
                        "date": datetime.now().strftime("%Y-%m-%d")
                    }
                    
                    result = book_slot(booking_data)
                    if result["status"] == "success":
                        reply_message = f"✨ Booking Confirmed! ✨\n\nService: {service.name}\nBarber: {session['barber']}\nTime: {selected_time}\n\nSee you soon!"
                    else:
                        reply_message = "Sorry, that slot is no longer available. Please try again."
                    clear_session(phone)
                except (IndexError, ValueError):
                    reply_message = "Invalid selection. Please choose a valid number."
                except Exception as e:
                    logger.error(f"Error booking slot: {str(e)}")
                    reply_message = "Sorry, there was an error. Please try again."
                    clear_session(phone)
            
            else:
                reply_message = "I don't understand. Please say 'hi' to start booking or 'restart' to start over."
            
            logger.info(f"Sending reply: {reply_message}")
            return {"reply": reply_message}
            
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            return {"reply": "Sorry, there was an error processing your message. Please try again."}
            
    except Exception as e:
        logger.error(f"Error in WhatsApp webhook: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 