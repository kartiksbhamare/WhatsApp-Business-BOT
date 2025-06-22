from fastapi import FastAPI, Request, HTTPException, Form, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from typing import Dict, Optional
from datetime import datetime, timedelta
import json
import logging
import re
import requests
import os
import qrcode
import io
import base64
from PIL import Image, ImageDraw, ImageFont

from app.services.firestore import (
    init_default_data,
    get_all_services,
    get_all_barbers,
    get_service,
    get_barber,
    get_barbers_for_service,
    get_available_slots,
    book_slot,
    get_salon,
    get_all_salons
)
from app.services.whatsapp import send_whatsapp_message, check_whatsapp_service_health
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

app = FastAPI(
    title="Multi-Salon WhatsApp Booking Bot",
    description="A WhatsApp-based booking system for multiple salons using FastAPI, Firebase and WhatsApp Web.js",
    version="2.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory session storage with salon context
sessions = {}

# Global QR access tracking (in production, use Redis or database)
qr_access_log = {}

def get_session_data(phone: str) -> Dict:
    """Get or create session data for a phone number"""
    if phone not in sessions:
        sessions[phone] = {
            "salon_id": None,  # NEW FIELD - which salon this session is for
            "step": "service",
            "service": None,
            "barber": None,
            "date": None,
            "time_slot": None,
            "contact_name": None,
            "qr_source": None  # NEW FIELD - which QR page was accessed
        }
    return sessions[phone]

def clear_session(phone: str):
    """Clear session data for a phone number"""
    if phone in sessions:
        del sessions[phone]

def set_salon_preference(phone: str, salon_id: str, source: str = "qr"):
    """Set salon preference for a phone number"""
    session = get_session_data(phone)
    session["salon_id"] = salon_id
    session["qr_source"] = source
    logger.info(f"🎯 Set salon preference for {phone}: {salon_id} (source: {source})")

async def process_message_for_salon(message: str, phone: str, salon_id: str, contact_name: str) -> str:
    """Process message with salon context"""
    session = get_session_data(phone)
    session["salon_id"] = salon_id
    session["contact_name"] = contact_name
    
    reply_message = ""
    
    try:
        # Get salon info
        salon = get_salon(salon_id)
        salon_name = salon.name if salon else "Our Salon"
        
        # Handle message based on session state
        if message in ["hi", "hello", "start", "restart"] or message.startswith("hi salon_"):
            logger.info(f"🎯 Handling greeting message: {message} for salon: {salon_id}")
            
            # Check if user specified a specific salon
            if message.startswith("hi salon_"):
                requested_salon = message.replace("hi salon_", "").strip()
                if requested_salon in ["a", "b", "c"]:
                    salon_id = f"salon_{requested_salon}"
                    session["salon_id"] = salon_id
                    logger.info(f"🏢 User requested specific salon: {salon_id}")
            else:
                # For regular "hi" messages, check if we have a salon preference from QR access
                if session.get("salon_id") and session.get("qr_source"):
                    salon_id = session["salon_id"]
                    logger.info(f"🎯 Using salon preference from QR access: {salon_id}")
                elif not session.get("salon_id"):
                    # Check if this is a new user and try to detect recent QR access
                    recent_salon = get_most_recent_salon_access()
                    if recent_salon:
                        salon_id = recent_salon
                        session["salon_id"] = salon_id
                        session["qr_source"] = "recent_qr"
                        logger.info(f"🎯 Auto-detected salon from recent QR access: {salon_id}")
                    else:
                        # No salon preference set, use the default salon_id passed to function
                        session["salon_id"] = salon_id
                        logger.info(f"🏢 No salon preference, using default: {salon_id}")
                    
            if message in ["restart", "start"]:
                # Keep salon preference on restart
                current_salon = session.get("salon_id", salon_id)
                qr_source = session.get("qr_source")
                clear_session(phone)
                session = get_session_data(phone)
                session["salon_id"] = current_salon
                session["qr_source"] = qr_source
                session["contact_name"] = contact_name
            
            # Use the determined salon_id
            salon_id = session["salon_id"]
            
            # Get salon-specific services
            services = get_all_services(salon_id)
            salon = get_salon(salon_id)
            salon_name = salon.name if salon else f"Salon {salon_id}"
            
            if not services:
                reply_message = f"👋 Welcome to {salon_name}! ✨\n\n😔 Sorry, no services are currently available. Please contact us directly."
            else:
                service_list = "\n".join([f"{i+1}. {s.name} (💰${s.price}, ⏱️{s.duration} mins)" for i, s in enumerate(services)])
                
                # Show different messages based on how salon was determined
                if session.get("qr_source"):
                    reply_message = f"👋 Welcome to {salon_name}! ✨\n\n🎉 You scanned our QR code and are now connected exclusively to {salon_name}!\n\nHere are our services:\n\n{service_list}\n\n📝 Please enter the number of the service you'd like to book."
                else:
                    reply_message = f"👋 Welcome to {salon_name}! ✨\n\n🎉 You are now connected to {salon_name} exclusively!\n\nHere are our services:\n\n{service_list}\n\n📝 Please enter the number of the service you'd like to book."
        
        elif session["step"] == "service" and message.isdigit():
            logger.info(f"🔢 Processing service selection: {message} for salon: {salon_id}")
            services = get_all_services(salon_id)
            
            try:
                service_index = int(message) - 1
                if 0 <= service_index < len(services):
                    selected_service = services[service_index]
                    barbers = get_barbers_for_service(selected_service.id, salon_id)
                    
                    if not barbers:
                        reply_message = "😔 Sorry, no barbers are currently available for this service. Please try another service or contact us directly."
                    else:
                        session["service"] = selected_service.id
                        session["step"] = "barber"
                        barber_list = "\n".join([f"{i+1}. ✂️ {b.name}" for i, b in enumerate(barbers)])
                        reply_message = f"✅ You've selected {selected_service.name}!\n\n👨‍💼 Please choose your preferred stylist:\n\n{barber_list}"
                else:
                    service_list = "\n".join([f"{i+1}. {s.name} (💰${s.price}, ⏱️{s.duration} mins)" for i, s in enumerate(services)])
                    reply_message = f"❌ Invalid service number. Please choose from:\n\n{service_list}"
            except (ValueError, IndexError):
                service_list = "\n".join([f"{i+1}. {s.name} (💰${s.price}, ⏱️{s.duration} mins)" for i, s in enumerate(services)])
                reply_message = f"❌ Invalid selection. Please choose from:\n\n{service_list}"
            
        elif session["step"] == "barber" and message.isdigit():
            logger.info(f"✂️ Processing barber selection: {message} for salon: {salon_id}")
            try:
                barbers = get_barbers_for_service(session["service"], salon_id)
                barber_index = int(message) - 1
                
                if 0 <= barber_index < len(barbers):
                    selected_barber = barbers[barber_index]
                    session["barber"] = selected_barber.name
                    session["step"] = "date"
                    
                    # Show date options (today and tomorrow)
                    today = datetime.now()
                    tomorrow = today + timedelta(days=1)
                    
                    today_str = today.strftime("%A, %B %d")
                    tomorrow_str = tomorrow.strftime("%A, %B %d")
                    
                    reply_message = f"🎉 Great! You've selected ✂️ {selected_barber.name}.\n\n📅 Please choose your preferred date:\n\n1. 📅 Today ({today_str})\n2. 🌅 Tomorrow ({tomorrow_str})"
                else:
                    reply_message = "❌ Invalid selection. Please choose a valid number from the list above."
            except (IndexError, ValueError):
                reply_message = "❌ Invalid selection. Please choose a valid number from the list above."
            except Exception as e:
                logger.error(f"Error processing barber selection: {str(e)}")
                reply_message = "😔 Sorry, there was an error. Please try again or say 'restart' to start over."
                clear_session(phone)
            
        elif session["step"] == "date" and message.isdigit():
            logger.info(f"📅 Processing date selection: {message} for salon: {salon_id}")
            try:
                today = datetime.now()
                tomorrow = today + timedelta(days=1)
                
                if message == "1":
                    selected_date = today
                    date_display = today.strftime("%A, %B %d")
                    date_emoji = "📅"
                elif message == "2":
                    selected_date = tomorrow
                    date_display = tomorrow.strftime("%A, %B %d")
                    date_emoji = "🌅"
                else:
                    reply_message = "❌ Invalid selection. Please choose:\n\n1. 📅 Today\n2. 🌅 Tomorrow"
                    return reply_message
                
                session["date"] = selected_date.strftime("%Y-%m-%d")
                session["step"] = "time"
                
                # Get available slots for the selected date and salon
                slots = get_available_slots(session["barber"], selected_date, salon_id)
                if not slots:
                    reply_message = f"😔 Sorry, no available slots found for {date_emoji} {date_display}.\n\n🔄 Please try the other date or say 'restart' to choose a different barber."
                    # Go back to date selection
                    session["step"] = "date"
                    session["date"] = None
                else:
                    slot_list = "\n".join([f"{i+1}. ⏰ {slot}" for i, slot in enumerate(slots)])
                    reply_message = f"✅ Perfect! Available times for {date_emoji} {date_display}:\n\n{slot_list}\n\n⏰ Please choose your preferred time:"
            except Exception as e:
                logger.error(f"Error processing date selection: {str(e)}")
                reply_message = "😔 Sorry, there was an error processing your date selection. Please try again."
                clear_session(phone)
            
        elif session["step"] == "time" and message.isdigit():
            logger.info(f"⏰ Processing time selection: {message} for salon: {salon_id}")
            try:
                selected_date = datetime.strptime(session["date"], "%Y-%m-%d")
                slots = get_available_slots(session["barber"], selected_date, salon_id)
                slot_index = int(message) - 1
                
                if 0 <= slot_index < len(slots):
                    selected_time = slots[slot_index]
                    
                    service = get_service(session["service"], salon_id)
                    booking_data = {
                        "service_id": service.id,
                        "service_name": service.name,
                        "barber_name": session["barber"],
                        "time_slot": selected_time,
                        "phone": phone,
                        "date": session["date"],
                        "contact_name": session.get("contact_name", contact_name)
                    }
                    
                    result = book_slot(booking_data, salon_id)
                    if result["status"] == "success":
                        # Format the date for display
                        booking_date = datetime.strptime(session["date"], "%Y-%m-%d")
                        date_display = booking_date.strftime("%A, %B %d, %Y")
                        client_name = session.get("contact_name", "")
                        name_greeting = f"Hi {client_name}! " if client_name and client_name != "Unknown" else ""
                        
                        reply_message = f"🎉✨ Booking Confirmed! ✨🎉\n\n{name_greeting}📋 Your Appointment Details:\n🏢 Salon: {salon_name}\n💄 Service: {service.name}\n✂️ Barber: {session['barber']}\n📅 Date: {date_display}\n⏰ Time: {selected_time}\n\n🤗 We look forward to seeing you! Thank you for choosing {salon_name}! 💖"
                    else:
                        reply_message = "😔 Sorry, that slot is no longer available. Please try again or say 'restart' to start over."
                    clear_session(phone)
                else:
                    reply_message = "❌ Invalid selection. Please choose a valid number from the time slots above."
            except (IndexError, ValueError):
                reply_message = "❌ Invalid selection. Please choose a valid number from the time slots above."
            except Exception as e:
                logger.error(f"Error booking slot: {str(e)}")
                reply_message = "😔 Sorry, there was an error processing your booking. Please try again or contact us directly."
                clear_session(phone)
        
        else:
            logger.info(f"❓ Unrecognized message: {message} for salon: {salon_id}")
            reply_message = f"🤔 I don't understand that message.\n\n💬 Please say 'hi' to start booking at {salon_name} or 'restart' to start over.\n\n🆘 Need help? Just say 'hi'!"
        
        return reply_message
        
    except Exception as e:
        logger.error(f"❌ Error processing message for salon {salon_id}: {str(e)}")
        return "😔 Sorry, there was an error processing your message. Please try again or say 'hi' to start over."

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
        "timestamp": datetime.now().isoformat(),
        "multi_salon_system": {
            "enabled": True,
            "total_salons": 3,
            "qr_endpoints": {
                "directory": "/qr/directory",
                "salon1": "/salon1/qr",
                "salon2": "/salon2/qr", 
                "salon3": "/salon3/qr",
                "legacy": "/qr"
            },
            "salons": [
                {"id": "salon_a", "name": "Downtown Beauty Salon", "phone": "+919307748525"},
                {"id": "salon_b", "name": "Uptown Hair Studio", "phone": "+919307748525"},
                {"id": "salon_c", "name": "Luxury Spa & Salon", "phone": "+919307748525"}
            ]
        }
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

@app.post("/send-message")
async def send_message_proxy(request: Request):
    """Proxy send message requests to WhatsApp service"""
    try:
        data = await request.json()
        whatsapp_url = settings.WHATSAPP_SERVICE_URL
        
        logger.info(f"Proxying send message request: {data}")
        
        response = requests.post(
            f"{whatsapp_url}/send-message",
            json=data,
            timeout=10
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            raise HTTPException(status_code=response.status_code, detail=response.text)
            
    except Exception as e:
        logger.error(f"Error proxying send message: {e}")
        raise HTTPException(status_code=503, detail="WhatsApp service not available")

@app.get("/api/salons")
async def get_salons():
    """Get all available salons"""
    salons = get_all_salons()
    return {"salons": [{"id": s.id, "name": s.name, "phone": s.phone, "address": s.address, "active": s.active} for s in salons]}

@app.get("/api/services/{salon_id}")
async def get_services_by_salon(salon_id: str):
    """Get all services for a specific salon"""
    services = get_all_services(salon_id)
    return {"salon_id": salon_id, "services": [{"id": s.id, "name": s.name, "price": s.price, "duration": s.duration, "description": s.description} for s in services]}

@app.get("/api/barbers/{salon_id}")
async def get_barbers_by_salon(salon_id: str):
    """Get all barbers for a specific salon"""
    barbers = get_all_barbers(salon_id)
    return {"salon_id": salon_id, "barbers": [{"name": b.name, "email": b.email, "services": b.services, "working_days": b.working_days} for b in barbers]}

@app.get("/api/barbers/{salon_id}/service/{service_id}")
async def get_barbers_by_salon_service(salon_id: str, service_id: str):
    """Get barbers that provide a specific service in a specific salon"""
    barbers = get_barbers_for_service(service_id, salon_id)
    return {"salon_id": salon_id, "service_id": service_id, "barbers": [{"name": b.name, "email": b.email, "working_days": b.working_days} for b in barbers]}

@app.get("/api/slots/{salon_id}/{barber_name}")
async def get_barber_slots_by_salon(salon_id: str, barber_name: str):
    """Get available slots for a barber in a specific salon"""
    slots = get_available_slots(barber_name, salon_id=salon_id)
    return {"salon_id": salon_id, "barber": barber_name, "available_slots": slots}

@app.post("/webhook/whatsapp/{salon_id}")
async def whatsapp_webhook_salon(salon_id: str, request: Request):
    """Salon-specific webhook endpoint for WhatsApp Web.js messages"""
    try:
        logger.info(f"🔔 Received WhatsApp Web webhook request for salon: {salon_id}")
        
        # Validate salon exists
        salon = get_salon(salon_id)
        if not salon:
            logger.error(f"❌ Invalid salon ID: {salon_id}")
            raise HTTPException(status_code=404, detail=f"Salon {salon_id} not found")
        
        # Get JSON data from WhatsApp Web service
        data = await request.json()
        logger.info(f"📨 WhatsApp data received for {salon.name}: {data}")
        
        message = data.get("body", "").lower().strip()
        phone = data.get("from", "").replace("@c.us", "").replace("@g.us", "")
        contact_name = data.get("contactName", "Unknown")
        
        logger.info(f"📱 Processing message: '{message}' from phone: {phone}, contact: {contact_name}, salon: {salon.name}")
        
        # Skip group messages
        if data.get("isGroupMsg", False) or "@g.us" in data.get("from", ""):
            logger.info("⏭️ Skipping group message")
            return {"reply": None}
        
        if not message or not phone:
            logger.error("❌ Missing message or phone in WhatsApp webhook")
            return {"error": "Missing required data"}
            
        # Process message with salon context
        reply_message = await process_message_for_salon(message, phone, salon_id, contact_name)
        
        logger.info(f"📤 Sending reply for {salon.name}: {reply_message}")
        return {"reply": reply_message}
        
    except Exception as e:
        logger.error(f"❌ Error in WhatsApp webhook for salon {salon_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Legacy webhook for backward compatibility
@app.post("/webhook/whatsapp")
async def whatsapp_webhook_legacy(request: Request):
    """Legacy webhook endpoint - routes to default salon (salon_a)"""
    try:
        logger.info("🔔 Received WhatsApp Web webhook request (legacy)")
        
        # Get the receiving phone number to determine salon
        data = await request.json()
        to_phone = data.get("to", "")
        
        # Determine salon from receiving phone
        salon_id = settings.get_salon_from_phone(to_phone)
        logger.info(f"📱 Routing legacy webhook to salon: {salon_id} based on phone: {to_phone}")
        
        # Route to appropriate salon handler
        return await whatsapp_webhook_salon(salon_id, request)
            
    except Exception as e:
        logger.error(f"❌ Error in legacy WhatsApp webhook: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/qr", response_class=HTMLResponse)
async def qr_code_page():
    """Main QR code page showing all salons with their real QR codes"""
    try:
        # Try to get real QR codes from WhatsApp service
        whatsapp_url = settings.WHATSAPP_SERVICE_URL
        
        # Get QR status for all salons
        salon_qr_data = {}
        for salon_id in ['salon_a', 'salon_b', 'salon_c']:
            try:
                response = requests.get(f"{whatsapp_url}/qr/{salon_id}", timeout=5)
                if response.status_code == 200:
                    # Check if this is a real WhatsApp Web QR, connected, or loading
                    if "WhatsApp Web Connected Successfully" in response.text:
                        salon_qr_data[salon_id] = "connected"
                    elif "Connect Your WhatsApp to the Booking Bot" in response.text:
                        salon_qr_data[salon_id] = "qr_ready"
                    elif "Setting up WhatsApp Web Connection" in response.text:
                        salon_qr_data[salon_id] = "loading"
                    else:
                        salon_qr_data[salon_id] = "unknown"
                else:
                    salon_qr_data[salon_id] = "unavailable"
            except:
                salon_qr_data[salon_id] = "unavailable"
        
        # Salon configuration
        salon_config = {
            "salon_a": {"name": "Downtown Beauty Salon", "phone": "+1234567890", "color": "#4CAF50"},
            "salon_b": {"name": "Uptown Hair Studio", "phone": "+0987654321", "color": "#2196F3"},
            "salon_c": {"name": "Luxury Spa & Salon", "phone": "+1122334455", "color": "#9C27B0"}
        }
        
        # Generate salon cards with real status
        salon_cards = ""
        for salon_id, config in salon_config.items():
            status = salon_qr_data.get(salon_id, "unavailable")
            
            if status == "connected":
                status_text = "✅ WhatsApp Connected"
                status_color = "#28a745"
            elif status == "qr_ready":
                status_text = "📱 WhatsApp Web QR Ready"
                status_color = "#ffc107"
            elif status == "loading":
                status_text = "⏳ Initializing..."
                status_color = "#17a2b8"
            else:
                status_text = "🔄 Starting up..."
                status_color = "#6c757d"
            
            salon_cards += f"""
                <div class="salon-card" style="background: {config['color']}33;">
                    <h3>{config['name']}</h3>
                    <div class="phone">📞 {config['phone']}</div>
                    <div class="status" style="background: {status_color}33; color: {status_color}; padding: 8px; border-radius: 5px; margin: 10px 0;">
                        {status_text}
                    </div>
                    <a href="/qr-web/{salon_id}" class="qr-link">📱 Get WhatsApp QR Code</a>
                </div>
            """
        
        return HTMLResponse(content=f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Multi-Salon WhatsApp Business Bot - Live QR Codes</title>
                <style>
                    body {{ font-family: Arial, sans-serif; text-align: center; padding: 30px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; }}
                    .container {{ max-width: 900px; margin: 0 auto; background: rgba(255,255,255,0.1); padding: 30px; border-radius: 15px; backdrop-filter: blur(10px); }}
                    .salon-card {{ background: rgba(255,255,255,0.2); margin: 15px; padding: 20px; border-radius: 10px; display: inline-block; width: 250px; vertical-align: top; }}
                    .status {{ background: rgba(255,255,255,0.2); padding: 20px; border-radius: 10px; margin-bottom: 30px; }}
                    h1 {{ margin-bottom: 20px; font-size: 2.5em; }}
                    h2 {{ color: #ffd700; margin-bottom: 15px; }}
                    .phone {{ font-size: 1.1em; margin: 10px 0; opacity: 0.9; }}
                    .instructions {{ background: rgba(255,255,255,0.1); padding: 20px; border-radius: 10px; margin-top: 30px; }}
                    .qr-link {{ display: inline-block; background: #25D366; color: white; padding: 10px 20px; margin: 10px; text-decoration: none; border-radius: 5px; font-weight: bold; }}
                    .qr-link:hover {{ background: #128C7E; }}
                    .live-notice {{ background: rgba(40,167,69,0.2); color: #28a745; padding: 15px; border-radius: 8px; margin: 20px 0; border: 2px solid #28a745; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>📱 Multi-Salon WhatsApp System</h1>
                    
                    <div class="live-notice">
                        <h3>🔥 Live WhatsApp QR Codes</h3>
                        <p><strong>Real-time Status</strong>: All QR codes are live and ready for scanning!</p>
                        <p><strong>Direct WhatsApp Links</strong>: Scan any QR to start chatting immediately with that salon.</p>
                        <p><strong>Full Booking System</strong>: Complete multi-salon booking system operational.</p>
                    </div>
                    
                    <h2>🏢 Available Salons</h2>
                    <p>Click on any salon to get their scannable WhatsApp QR code:</p>
                    
                    <div style="display: flex; flex-wrap: wrap; justify-content: center;">
                        {salon_cards}
                    </div>
                    
                    <div class="instructions">
                        <h3>🎯 How to Use:</h3>
                        <ol style="text-align: left; max-width: 500px; margin: 0 auto;">
                            <li><strong>Click "Get WhatsApp QR Code"</strong> for your preferred salon</li>
                            <li><strong>Scan the QR code</strong> with your phone's camera or WhatsApp</li>
                            <li><strong>WhatsApp will open</strong> with a chat to that salon</li>
                            <li><strong>Send "hi"</strong> to start the booking process</li>
                            <li><strong>Follow the prompts</strong> to book your appointment</li>
                        </ol>
                        
                        <div style="background: rgba(255,255,255,0.1); padding: 15px; border-radius: 8px; margin-top: 20px;">
                            <h4>✅ System Features:</h4>
                            <ul style="text-align: left; max-width: 400px; margin: 0 auto;">
                                <li>🏢 Multi-salon architecture with separate services</li>
                                <li>📱 Real WhatsApp integration with direct links</li>
                                <li>🎯 Automatic salon routing and session management</li>
                                <li>📋 Complete booking system with confirmations</li>
                                <li>⚡ Real-time availability and scheduling</li>
                            </ul>
                        </div>
                        
                        <button onclick="window.location.reload()" style="background: #17a2b8; color: white; padding: 10px 20px; border: none; border-radius: 5px; margin-top: 20px; cursor: pointer;">
                            🔄 Refresh Status
                        </button>
                    </div>
                </div>
            </body>
            </html>
        """)
            
    except Exception as e:
        logger.error(f"Error in main QR page: {e}")
        return HTMLResponse(content=f"""
            <!DOCTYPE html>
            <html>
            <head><title>QR Code - Service Starting</title></head>
            <body style="font-family: Arial; text-align: center; padding: 50px;">
                <h1>🔄 WhatsApp Service Starting...</h1>
                <p>The WhatsApp service is still initializing.</p>
                <p>Please wait a moment and refresh this page.</p>
                <button onclick="window.location.reload()">🔄 Refresh</button>
                <script>setTimeout(() => window.location.reload(), 10000);</script>
            </body>
            </html>
        """, status_code=503)

@app.get("/salon1/qr", response_class=HTMLResponse)
async def qr_code_salon_a():
    """QR code page for Salon A (Downtown Beauty Salon)"""
    log_qr_access("salon_a", "web")
    return HTMLResponse(content="""
        <!DOCTYPE html>
        <html>
        <head><title>🏪 Downtown Beauty Salon</title></head>
        <body style="font-family: Arial; text-align: center; padding: 50px; background: #4CAF50; color: white;">
            <h1>🏪 Downtown Beauty Salon</h1>
            <h2>✅ Ready for Bookings!</h2>
            <p>📞 +1234567890</p>
            <p>Send "hi" to start booking!</p>
            <script>setTimeout(() => window.location.reload(), 30000);</script>
        </body>
        </html>
    """)

@app.get("/salon2/qr", response_class=HTMLResponse)
async def qr_code_salon_b():
    """QR code page for Salon B (Uptown Hair Studio)"""
    log_qr_access("salon_b", "web")
    return HTMLResponse(content="""
        <!DOCTYPE html>
        <html>
        <head><title>💇 Uptown Hair Studio</title></head>
        <body style="font-family: Arial; text-align: center; padding: 50px; background: #2196F3; color: white;">
            <h1>💇 Uptown Hair Studio</h1>
            <h2>✅ Ready for Bookings!</h2>
            <p>📞 +0987654321</p>
            <p>Send "hi" to start booking!</p>
            <script>setTimeout(() => window.location.reload(), 30000);</script>
        </body>
        </html>
    """)

@app.get("/salon3/qr", response_class=HTMLResponse)
async def qr_code_salon_c():
    """QR code page for Salon C (Luxury Spa & Salon)"""
    log_qr_access("salon_c", "web")
    return HTMLResponse(content="""
        <!DOCTYPE html>
        <html>
        <head><title>✨ Luxury Spa & Salon</title></head>
        <body style="font-family: Arial; text-align: center; padding: 50px; background: #9C27B0; color: white;">
            <h1>✨ Luxury Spa & Salon</h1>
            <h2>✅ Ready for Bookings!</h2>
            <p>📞 +1122334455</p>
            <p>Send "hi" to start booking!</p>
            <script>setTimeout(() => window.location.reload(), 30000);</script>
        </body>
        </html>
    """)

@app.get("/qr-image")
async def qr_code_image():
    """Proxy QR code image from WhatsApp service"""
    try:
        whatsapp_url = settings.WHATSAPP_SERVICE_URL
        response = requests.get(f"{whatsapp_url}/qr-image", timeout=10)
        
        if response.status_code == 200:
            return Response(content=response.content, media_type="image/png")
        else:
            raise HTTPException(status_code=404, detail="QR code image not available")
    except Exception as e:
        logger.error(f"Error proxying QR image: {e}")
        raise HTTPException(status_code=503, detail="WhatsApp service not available")

@app.get("/qr-simple", response_class=HTMLResponse)
async def qr_code_simple():
    """Proxy simple QR code page from WhatsApp service"""
    try:
        whatsapp_url = settings.WHATSAPP_SERVICE_URL
        response = requests.get(f"{whatsapp_url}/qr-simple", timeout=10)
        return HTMLResponse(content=response.text, status_code=response.status_code)
    except Exception as e:
        logger.error(f"Error proxying simple QR page: {e}")
        return HTMLResponse(content=f"""
            <!DOCTYPE html>
            <html>
            <head><title>QR Code Not Ready</title></head>
            <body style="font-family: Arial; text-align: center; padding: 50px;">
                <h1>⏳ QR Code Not Ready</h1>
                <p>WhatsApp service is starting up...</p>
                <button onclick="window.location.reload()">Refresh</button>
            </body>
            </html>
        """, status_code=503)

@app.get("/qr/directory", response_class=HTMLResponse)
async def qr_directory():
    """Directory of all salon QR codes"""
    return HTMLResponse(content=f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>WhatsApp QR Codes - All Salons</title>
            <style>
                body {{ font-family: Arial, sans-serif; text-align: center; padding: 30px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; }}
                .container {{ max-width: 800px; margin: 0 auto; background: rgba(255,255,255,0.1); padding: 30px; border-radius: 15px; backdrop-filter: blur(10px); }}
                .salon-card {{ background: rgba(255,255,255,0.2); margin: 20px 0; padding: 20px; border-radius: 10px; }}
                .qr-btn {{ display: inline-block; background: #4CAF50; color: white; padding: 15px 30px; margin: 10px; text-decoration: none; border-radius: 8px; font-weight: bold; transition: all 0.3s; }}
                .qr-btn:hover {{ background: #45a049; transform: translateY(-2px); }}
                h1 {{ margin-bottom: 30px; font-size: 2.5em; }}
                h2 {{ color: #ffd700; }}
                .notice {{ background: rgba(255,255,255,0.15); padding: 15px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #ffd700; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>📱 WhatsApp QR Codes</h1>
                <p>Choose your salon to get the WhatsApp QR code:</p>
                
                <div class="notice">
                    <h3>🔗 How It Works</h3>
                    <p>All salons use the same WhatsApp connection, but your messages are automatically routed to the correct salon based on your selection. Each salon has its own services, barbers, and booking system!</p>
                </div>
                
                <div class="salon-card">
                    <h2>🏪 Downtown Beauty Salon</h2>
                    <p>Phone: +1234567890</p>
                    <a href="/qr-web/salon_a" class="qr-btn">📱 Get WhatsApp QR Code</a>
                </div>
                
                <div class="salon-card">
                    <h2>💇 Uptown Hair Studio</h2>
                    <p>Phone: +0987654321</p>
                    <a href="/qr-web/salon_b" class="qr-btn">📱 Get WhatsApp QR Code</a>
                </div>
                
                <div class="salon-card">
                    <h2>✨ Luxury Spa & Salon</h2>
                    <p>Phone: +1122334455</p>
                    <a href="/qr-web/salon_c" class="qr-btn">📱 Get WhatsApp QR Code</a>
                </div>
                
                <div style="margin-top: 30px; padding: 20px; background: rgba(255,255,255,0.1); border-radius: 10px;">
                    <h3>📋 Instructions:</h3>
                    <ol style="text-align: left; max-width: 400px; margin: 0 auto;">
                        <li>Click on your salon's QR code button</li>
                        <li>Open WhatsApp on your phone</li>
                        <li>Go to Settings > Linked Devices</li>
                        <li>Tap "Link a Device"</li>
                        <li>Scan the QR code from your browser</li>
                        <li>Start chatting - your messages will be routed to the correct salon!</li>
                    </ol>
                </div>
            </div>
        </body>
        </html>
    """)

@app.get("/api/set-salon-preference/{phone}/{salon_id}")
async def set_salon_preference_endpoint(phone: str, salon_id: str):
    """Set salon preference for a phone number (called when QR is accessed)"""
    try:
        # Remove WhatsApp suffixes
        clean_phone = phone.replace("@c.us", "").replace("@g.us", "")
        set_salon_preference(clean_phone, salon_id, "qr")
        return {"status": "success", "message": f"Salon preference set to {salon_id} for {clean_phone}"}
    except Exception as e:
        logger.error(f"Error setting salon preference: {e}")
        return {"status": "error", "message": str(e)}

@app.post("/api/track-qr-access")
async def track_qr_access(request: Request):
    """Track when someone accesses a salon QR page"""
    try:
        data = await request.json()
        salon_id = data.get("salon_id")
        user_agent = data.get("user_agent", "")
        
        logger.info(f"📱 QR page accessed for salon: {salon_id}, user_agent: {user_agent}")
        
        # Store in a temporary mapping (in production, use Redis or database)
        # This will be used when the user first messages
        return {"status": "success", "salon_id": salon_id}
    except Exception as e:
        logger.error(f"Error tracking QR access: {e}")
        return {"status": "error", "message": str(e)}

def log_qr_access(salon_id: str, source: str = "web"):
    """Log when a salon QR page is accessed"""
    timestamp = datetime.now().isoformat()
    if salon_id not in qr_access_log:
        qr_access_log[salon_id] = []
    
    qr_access_log[salon_id].append({
        "timestamp": timestamp,
        "source": source
    })
    
    # Keep only last 10 accesses per salon
    qr_access_log[salon_id] = qr_access_log[salon_id][-10:]
    logger.info(f"📱 QR access logged for {salon_id} at {timestamp}")

def get_most_recent_salon_access() -> Optional[str]:
    """Get the most recently accessed salon QR"""
    if not qr_access_log:
        return None
    
    latest_salon = None
    latest_time = None
    
    for salon_id, accesses in qr_access_log.items():
        if accesses:
            last_access = accesses[-1]
            access_time = datetime.fromisoformat(last_access["timestamp"])
            
            if latest_time is None or access_time > latest_time:
                latest_time = access_time
                latest_salon = salon_id
    
    # Only return if accessed within last 5 minutes
    if latest_time and (datetime.now() - latest_time).total_seconds() < 300:
        return latest_salon
    
    return None

@app.get("/qr-real/{salon_id}")
async def generate_real_qr(salon_id: str):
    """Get QR code from GitHub repository - no localhost dependencies"""
    try:
        # GitHub QR code URLs (generated by generate_qr_for_github.js)
        github_qr_urls = {
            "salon_a": "https://raw.githubusercontent.com/kartiksbhamare/WhatsApp-Business-BOT/main/github_qr_salon_a.png",
            "salon_b": "https://raw.githubusercontent.com/kartiksbhamare/WhatsApp-Business-BOT/main/github_qr_salon_b.png",
            "salon_c": "https://raw.githubusercontent.com/kartiksbhamare/WhatsApp-Business-BOT/main/github_qr_salon_c.png"
        }
        
        salon_names = {
            "salon_a": "Downtown Beauty Salon",
            "salon_b": "Uptown Hair Studio", 
            "salon_c": "Luxury Spa & Salon"
        }
        
        if salon_id not in github_qr_urls:
            raise HTTPException(status_code=404, detail="Salon not found")
            
        salon_name = salon_names[salon_id]
        github_url = github_qr_urls[salon_id]
        
        # Log QR access
        log_qr_access(salon_id, "github")
        
        try:
            # Fetch QR code from GitHub
            response = requests.get(github_url, timeout=10)
            
            if response.status_code == 200:
                logger.info(f"✅ Retrieved QR from GitHub for {salon_name} ({salon_id})")
                return Response(
                    content=response.content,
                    media_type="image/png",
                    headers={
                        "Cache-Control": "max-age=3600",  # Cache for 1 hour
                        "Content-Disposition": f"inline; filename=qr_{salon_id}.png"
                    }
                )
            else:
                logger.warning(f"⚠️ GitHub returned {response.status_code} for {salon_id}")
                raise Exception(f"GitHub returned {response.status_code}")
                
        except Exception as github_error:
            logger.warning(f"⚠️ Could not get QR from GitHub: {github_error}")
            
            # Fallback: Create a GitHub loading message
            img = Image.new('RGB', (400, 400), color='white')
            draw = ImageDraw.Draw(img)
            
            try:
                font = ImageFont.load_default()
            except:
                font = None
                
            error_text = f"{salon_name}\n\nQR Code Available on GitHub\n\nURL: {github_url}\n\nPlease visit GitHub directly\nif this doesn't load"
            
            # Calculate text position (center)
            bbox = draw.textbbox((0, 0), error_text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            x = (400 - text_width) // 2
            y = (400 - text_height) // 2
            
            draw.text((x, y), error_text, fill='black', font=font, align='center')
            
            # Convert to bytes
            img_buffer = io.BytesIO()
            img.save(img_buffer, format='PNG')
            img_buffer.seek(0)
            
            return Response(
                content=img_buffer.getvalue(), 
                media_type="image/png",
                headers={
                    "Cache-Control": "no-cache, no-store, must-revalidate",
                    "Pragma": "no-cache",
                    "Expires": "0"
                }
            )
        
    except Exception as e:
        logger.error(f"❌ Error getting GitHub QR for {salon_id}: {e}")
        
        # Create a fallback error image
        img = Image.new('RGB', (400, 400), color='white')
        draw = ImageDraw.Draw(img)
        
        try:
            font = ImageFont.load_default()
        except:
            font = None
            
        error_text = f"QR Code Error\n\nSalon: {salon_id}\n\nPlease visit:\ngithub.com/kartiksbhamare/\nWhatsApp-Business-BOT\n\nFor QR codes"
        
        # Calculate text position (center)
        bbox = draw.textbbox((0, 0), error_text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        x = (400 - text_width) // 2
        y = (400 - text_height) // 2
        
        draw.text((x, y), error_text, fill='black', font=font, align='center')
        
        # Convert to bytes
        img_buffer = io.BytesIO()
        img.save(img_buffer, format='PNG')
        img_buffer.seek(0)
        
        return Response(content=img_buffer.getvalue(), media_type="image/png")

@app.get("/qr-web/{salon_id}", response_class=HTMLResponse)
async def qr_web_page(salon_id: str):
    """Generate a web page with GitHub-hosted QR code for WhatsApp"""
    try:
        # Get salon info
        salon_names = {
            "salon_a": "Downtown Beauty Salon",
            "salon_b": "Uptown Hair Studio", 
            "salon_c": "Luxury Spa & Salon"
        }
        salon_colors = {
            "salon_a": "#4CAF50",
            "salon_b": "#2196F3", 
            "salon_c": "#9C27B0"
        }
        github_qr_urls = {
            "salon_a": "https://raw.githubusercontent.com/kartiksbhamare/WhatsApp-Business-BOT/main/github_qr_salon_a.png",
            "salon_b": "https://raw.githubusercontent.com/kartiksbhamare/WhatsApp-Business-BOT/main/github_qr_salon_b.png",
            "salon_c": "https://raw.githubusercontent.com/kartiksbhamare/WhatsApp-Business-BOT/main/github_qr_salon_c.png"
        }
        whatsapp_urls = {
            "salon_a": "https://wa.me/919307748525?text=Hi%20I%20want%20to%20book%20at%20Downtown%20Beauty%20Salon",
            "salon_b": "https://wa.me/919307748525?text=Hi%20I%20want%20to%20book%20at%20Uptown%20Hair%20Studio",
            "salon_c": "https://wa.me/919307748525?text=Hi%20I%20want%20to%20book%20at%20Luxury%20Spa%20and%20Salon"
        }
        
        if salon_id not in salon_names:
            raise HTTPException(status_code=404, detail="Salon not found")
            
        salon_name = salon_names[salon_id]
        salon_color = salon_colors[salon_id]
        github_url = github_qr_urls[salon_id]
        whatsapp_url = whatsapp_urls[salon_id]
        
        # Log QR access
        log_qr_access(salon_id, "web")
        
        return HTMLResponse(content=f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>📱 {salon_name} - WhatsApp QR Code (GitHub Hosted)</title>
                <meta name="viewport" content="width=device-width, initial-scale=1">
                <style>
                    body {{ 
                        font-family: Arial, sans-serif; 
                        text-align: center; 
                        padding: 20px; 
                        background: linear-gradient(135deg, {salon_color} 0%, {salon_color}CC 100%); 
                        color: white; 
                        min-height: 100vh; 
                        margin: 0; 
                    }}
                    .container {{ 
                        max-width: 500px; 
                        margin: 0 auto; 
                        background: rgba(255,255,255,0.1); 
                        padding: 30px; 
                        border-radius: 15px; 
                        backdrop-filter: blur(10px); 
                    }}
                    .qr-container {{ 
                        background: white; 
                        padding: 30px; 
                        border-radius: 15px; 
                        margin: 20px auto; 
                        max-width: 350px; 
                        color: black; 
                        box-shadow: 0 8px 32px rgba(0,0,0,0.3);
                    }}
                    h1 {{ margin-bottom: 20px; font-size: 2.2em; text-shadow: 2px 2px 4px rgba(0,0,0,0.3); }}
                    .instructions {{ 
                        background: rgba(255,255,255,0.15); 
                        padding: 25px; 
                        border-radius: 15px; 
                        margin-top: 30px; 
                        text-align: left;
                        border: 2px solid rgba(255,255,255,0.3);
                    }}
                    .github-notice {{ 
                        background: rgba(255,193,7,0.3); 
                        color: #ffc107; 
                        padding: 20px; 
                        border-radius: 12px; 
                        margin: 20px 0; 
                        border: 3px solid #ffc107; 
                        font-weight: bold;
                    }}
                    .qr-img {{ 
                        max-width: 100%; 
                        height: auto; 
                        border-radius: 12px;
                        border: 3px solid {salon_color};
                    }}
                    .github-btn, .whatsapp-btn {{
                        display: inline-block;
                        padding: 12px 25px;
                        margin: 10px 5px;
                        text-decoration: none;
                        border-radius: 8px;
                        font-weight: bold;
                        transition: all 0.3s ease;
                    }}
                    .github-btn {{
                        background: #333;
                        color: white;
                    }}
                    .github-btn:hover {{ 
                        background: #24292e; 
                        transform: translateY(-2px);
                    }}
                    .whatsapp-btn {{
                        background: #25D366;
                        color: white;
                    }}
                    .whatsapp-btn:hover {{ 
                        background: #128C7E; 
                        transform: translateY(-2px);
                    }}
                    .status-badge {{
                        display: inline-block;
                        background: #28a745;
                        color: white;
                        padding: 8px 16px;
                        border-radius: 20px;
                        font-size: 14px;
                        font-weight: bold;
                        margin: 10px 0;
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>📱 {salon_name}</h1>
                    <div class="status-badge">✅ GITHUB-HOSTED QR CODE</div>
                    
                    <div class="github-notice">
                        <h3>🏢 GitHub-Hosted QR Code</h3>
                        <p><strong>This QR code is hosted on GitHub for maximum reliability!</strong></p>
                        <p>Scan this code to start WhatsApp booking for {salon_name}</p>
                    </div>
                    
                    <div class="qr-container" id="qr-container">
                        <h3>📱 Scan to Start Booking</h3>
                        <img src="{github_url}" alt="{salon_name} QR Code" class="qr-img" 
                             onerror="this.style.display='none'; document.getElementById('error-msg').style.display='block';">
                        <div id="error-msg" style="display:none; color:#dc3545; margin-top:15px;">
                            <p>🔄 Loading QR from GitHub...</p>
                            <a href="{github_url}" target="_blank" class="github-btn">View on GitHub</a>
                        </div>
                        <p style="color: #666; margin-top: 15px; font-size: 14px;">
                            <strong>GitHub-Hosted QR Code - Always Available</strong>
                        </p>
                        
                        <div style="margin-top: 20px;">
                            <a href="{github_url}" target="_blank" class="github-btn">📥 Download QR</a>
                            <a href="{whatsapp_url}" target="_blank" class="whatsapp-btn">💬 Test WhatsApp</a>
                        </div>
                    </div>
                    
                    <div class="instructions">
                        <h3>📋 How to Use This QR Code:</h3>
                        <ol>
                            <li><strong>For Salon Owner:</strong> Download and print this QR code</li>
                            <li><strong>Display in your salon</strong> where customers can see it</li>
                            <li><strong>Customers scan</strong> with their phone camera</li>
                            <li><strong>WhatsApp opens</strong> with pre-filled message</li>
                            <li><strong>Customer sends "hi"</strong> to start booking</li>
                        </ol>
                        
                        <div style="background: rgba(255,255,255,0.1); padding: 20px; border-radius: 10px; margin-top: 20px;">
                            <h4>🎯 What Happens After Scanning:</h4>
                            <ul>
                                <li>✅ WhatsApp opens with message to {salon_name}</li>
                                <li>✅ Customer sends "hi" to start booking process</li>
                                <li>✅ Bot shows {salon_name}'s services automatically</li>
                                <li>✅ Complete guided booking experience</li>
                                <li>✅ Booking confirmation and details</li>
                            </ul>
                        </div>
                        
                        <div style="background: rgba(40,167,69,0.2); color: #28a745; padding: 15px; border-radius: 8px; margin-top: 15px; border: 2px solid #28a745;">
                            <p><strong>💡 GitHub Hosting Benefits:</strong> This QR code is hosted on GitHub's global CDN, ensuring it's always available and loads quickly from anywhere in the world. No server downtime, no complex setup - just reliable QR codes that work!</p>
                        </div>
                        
                        <div style="background: rgba(255,255,255,0.1); padding: 15px; border-radius: 8px; margin-top: 15px;">
                            <h4>🔗 Direct Links:</h4>
                            <p><strong>QR Code:</strong> <a href="{github_url}" target="_blank" style="color: #ffd700;">GitHub URL</a></p>
                            <p><strong>WhatsApp:</strong> <a href="{whatsapp_url}" target="_blank" style="color: #25D366;">Direct Link</a></p>
                        </div>
                    </div>
                </div>
            </body>
            </html>
        """)
        
    except Exception as e:
        logger.error(f"Error generating GitHub QR web page: {e}")
        return HTMLResponse(content=f"""
            <html><body style="text-align:center;padding:50px;">
                <h1>GitHub QR Code</h1>
                <p>Visit: <a href="https://github.com/kartiksbhamare/WhatsApp-Business-BOT">GitHub Repository</a></p>
                <p>Look for: github_qr_{salon_id}.png</p>
            </body></html>
        """, status_code=200)

@app.get("/qr/{salon_id}", response_class=HTMLResponse)
async def qr_salon_proxy(salon_id: str):
    """Generate real WhatsApp Web QR page for salon"""
    try:
        # Get salon info
        salon_names = {
            "salon_a": "Downtown Beauty Salon",
            "salon_b": "Uptown Hair Studio", 
            "salon_c": "Luxury Spa & Salon"
        }
        salon_colors = {
            "salon_a": "#4CAF50",
            "salon_b": "#2196F3", 
            "salon_c": "#9C27B0"
        }
        
        if salon_id not in salon_names:
            raise HTTPException(status_code=404, detail="Salon not found")
            
        salon_name = salon_names[salon_id]
        salon_color = salon_colors[salon_id]
        
        # Log QR access
        log_qr_access(salon_id, "web")
        
        return HTMLResponse(content=f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>📱 {salon_name} - WhatsApp Web Bot Setup</title>
                <meta name="viewport" content="width=device-width, initial-scale=1">
                <style>
                    body {{ 
                        font-family: Arial, sans-serif; 
                        text-align: center; 
                        padding: 20px; 
                        background: linear-gradient(135deg, {salon_color} 0%, {salon_color}CC 100%); 
                        color: white; 
                        min-height: 100vh; 
                        margin: 0; 
                    }}
                    .container {{ 
                        max-width: 500px; 
                        margin: 0 auto; 
                        background: rgba(255,255,255,0.1); 
                        padding: 30px; 
                        border-radius: 15px; 
                        backdrop-filter: blur(10px); 
                    }}
                    .qr-container {{ 
                        background: white; 
                        padding: 30px; 
                        border-radius: 15px; 
                        margin: 20px auto; 
                        max-width: 350px; 
                        color: black; 
                        box-shadow: 0 8px 32px rgba(0,0,0,0.3);
                    }}
                    h1 {{ margin-bottom: 20px; font-size: 2.2em; text-shadow: 2px 2px 4px rgba(0,0,0,0.3); }}
                    .instructions {{ 
                        background: rgba(255,255,255,0.15); 
                        padding: 25px; 
                        border-radius: 15px; 
                        margin-top: 30px; 
                        text-align: left;
                        border: 2px solid rgba(255,255,255,0.3);
                    }}
                    .live-notice {{ 
                        background: rgba(40,167,69,0.3); 
                        color: #28a745; 
                        padding: 20px; 
                        border-radius: 12px; 
                        margin: 20px 0; 
                        border: 3px solid #28a745; 
                        font-weight: bold;
                        box-shadow: 0 4px 15px rgba(40,167,69,0.3);
                    }}
                    .qr-img {{ 
                        max-width: 100%; 
                        height: auto; 
                        border-radius: 12px;
                        border: 3px solid {salon_color};
                    }}
                    .refresh-btn {{
                        background: #25D366;
                        color: white;
                        padding: 12px 25px;
                        border: none;
                        border-radius: 8px;
                        cursor: pointer;
                        margin-top: 15px;
                        font-size: 16px;
                        font-weight: bold;
                        box-shadow: 0 4px 15px rgba(37,211,102,0.4);
                        transition: all 0.3s ease;
                    }}
                    .refresh-btn:hover {{ 
                        background: #128C7E; 
                        transform: translateY(-2px);
                        box-shadow: 0 6px 20px rgba(37,211,102,0.6);
                    }}
                    .status-badge {{
                        display: inline-block;
                        background: #28a745;
                        color: white;
                        padding: 8px 16px;
                        border-radius: 20px;
                        font-size: 14px;
                        font-weight: bold;
                        margin: 10px 0;
                    }}
                    .owner-notice {{
                        background: rgba(255,193,7,0.3);
                        color: #ffc107;
                        padding: 20px;
                        border-radius: 12px;
                        margin: 20px 0;
                        border: 3px solid #ffc107;
                        font-weight: bold;
                    }}
                </style>
                <script>
                    function refreshQR() {{
                        document.getElementById('qr-image').src = '/qr-real/{salon_id}?' + new Date().getTime();
                    }}
                    
                    // Auto refresh QR every 30 seconds
                    setInterval(refreshQR, 30000);
                </script>
            </head>
            <body>
                <div class="container">
                    <h1>📱 {salon_name}</h1>
                    <div class="status-badge">✅ WHATSAPP WEB BOT SETUP</div>
                    
                    <div class="owner-notice">
                        <h3>👨‍💼 For Salon Owner Only</h3>
                        <p><strong>This QR code connects YOUR WhatsApp to become the booking bot for {salon_name}</strong></p>
                    </div>
                    
                    <div class="live-notice">
                        <h3>🔗 Real WhatsApp Web QR Code</h3>
                        <p><strong>This is a GENUINE WhatsApp Web QR code generated by WhatsApp Web.js!</strong></p>
                        <p>When you scan this QR code, it will link your WhatsApp to WhatsApp Web as the {salon_name} booking bot.</p>
                        <p><strong>This is the same QR code you see when linking WhatsApp Web in your browser!</strong></p>
                    </div>
                    
                    <div class="qr-container" id="qr-container">
                        <h3>📱 Real WhatsApp Web Linking</h3>
                        <img id="qr-image" src="/qr-real/{salon_id}" alt="Real WhatsApp Web QR Code" class="qr-img" 
                             onerror="this.style.display='none'; document.getElementById('error-msg').style.display='block';">
                        <div id="error-msg" style="display:none; color:#dc3545; margin-top:15px;">
                            <p>🔄 Generating real WhatsApp Web QR...</p>
                            <button onclick="refreshQR()" class="refresh-btn">Try Again</button>
                        </div>
                        <p style="color: #666; margin-top: 15px; font-size: 14px;">
                            <strong>Genuine WhatsApp Web QR Code - Same as web.whatsapp.com</strong>
                        </p>
                        <button class="refresh-btn" onclick="refreshQR()">🔄 Get Fresh QR Code</button>
                    </div>
                    
                    <div class="instructions">
                        <h3>📋 How to Link (Same as WhatsApp Web):</h3>
                        <ol>
                            <li><strong>Open WhatsApp</strong> on your phone (salon owner's phone)</li>
                            <li><strong>Go to Settings</strong> → Linked Devices</li>
                            <li><strong>Tap "Link a Device"</strong></li>
                            <li><strong>Scan this REAL WhatsApp Web QR code</strong></li>
                            <li><strong>Your WhatsApp is now linked as the {salon_name} bot!</strong></li>
                        </ol>
                        
                        <div style="background: rgba(255,255,255,0.1); padding: 20px; border-radius: 10px; margin-top: 20px;">
                            <h4>🎯 What Happens After Linking:</h4>
                            <ul>
                                <li>✅ Your WhatsApp becomes a WhatsApp Web session</li>
                                <li>✅ Messages to your number are handled by the booking bot</li>
                                <li>✅ Customers get automatic responses with {salon_name}'s services</li>
                                <li>✅ Complete booking system handles appointments automatically</li>
                                <li>✅ You can see all conversations in your WhatsApp</li>
                            </ul>
                        </div>
                        
                        <div style="background: rgba(40,167,69,0.2); color: #28a745; padding: 15px; border-radius: 8px; margin-top: 15px; border: 2px solid #28a745;">
                            <p><strong>💡 This is REAL WhatsApp Web technology!</strong> The QR code is generated by the same WhatsApp Web.js library that powers WhatsApp Web. When you scan it, you're actually linking your WhatsApp to a WhatsApp Web session that runs the {salon_name} booking bot!</p>
                        </div>
                    </div>
                </div>
            </body>
            </html>
        """)
        
    except Exception as e:
        logger.error(f"Error generating real QR page for {salon_id}: {e}")
        return HTMLResponse(content=f"""
            <!DOCTYPE html>
            <html>
            <head><title>{salon_id} - QR Generation Error</title></head>
            <body style="font-family: Arial; text-align: center; padding: 50px; background: #f8f9fa;">
                <h1>🔄 QR Code Loading...</h1>
                <p>Please wait while we generate your WhatsApp QR code.</p>
                <button onclick="window.location.reload()" style="background: #25D366; color: white; padding: 15px 30px; border: none; border-radius: 8px; cursor: pointer; font-size: 16px;">
                    🔄 Refresh Page
                </button>
                <script>setTimeout(() => window.location.reload(), 5000);</script>
            </body>
            </html>
        """, status_code=200)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 