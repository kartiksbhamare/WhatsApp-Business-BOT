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
            "contact_name": None
        }
    return sessions[phone]

def clear_session(phone: str):
    """Clear session data for a phone number"""
    if phone in sessions:
        del sessions[phone]

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
                    
            if message in ["restart", "start"]:
                clear_session(phone)
                session = get_session_data(phone)
                session["salon_id"] = salon_id
                session["contact_name"] = contact_name
            
            # Get salon-specific services
            services = get_all_services(salon_id)
            salon = get_salon(salon_id)
            salon_name = salon.name if salon else f"Salon {salon_id}"
            
            if not services:
                reply_message = f"👋 Welcome to {salon_name}! ✨\n\n😔 Sorry, no services are currently available. Please contact us directly."
            else:
                service_list = "\n".join([f"{i+1}. {s.name} (💰${s.price}, ⏱️{s.duration} mins)" for i, s in enumerate(services)])
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
                {"id": "salon_a", "name": "Downtown Beauty Salon", "phone": "+1234567890"},
                {"id": "salon_b", "name": "Uptown Hair Studio", "phone": "+0987654321"},
                {"id": "salon_c", "name": "Luxury Spa & Salon", "phone": "+1122334455"}
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
    """Main QR code page showing all salons with their QR codes"""
    try:
        # Check if WhatsApp is connected
        whatsapp_url = settings.WHATSAPP_SERVICE_URL
        response = requests.get(f"{whatsapp_url}/qr", timeout=10)
        
        if response.status_code == 200 and "Connected Successfully" in response.text:
            # WhatsApp is already connected - show connected status with salon info
            return HTMLResponse(content=f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <title>Multi-Salon WhatsApp Business Bot - Dashboard</title>
                    <style>
                        body {{ font-family: Arial, sans-serif; text-align: center; padding: 30px; background: linear-gradient(135deg, #4CAF50 0%, #45a049 100%); color: white; }}
                        .container {{ max-width: 900px; margin: 0 auto; background: rgba(255,255,255,0.1); padding: 30px; border-radius: 15px; backdrop-filter: blur(10px); }}
                        .salon-card {{ background: rgba(255,255,255,0.2); margin: 15px; padding: 20px; border-radius: 10px; display: inline-block; width: 250px; vertical-align: top; }}
                        .status {{ background: rgba(255,255,255,0.2); padding: 20px; border-radius: 10px; margin-bottom: 30px; }}
                        h1 {{ margin-bottom: 20px; font-size: 2.5em; }}
                        h2 {{ color: #ffd700; margin-bottom: 15px; }}
                        .phone {{ font-size: 1.1em; margin: 10px 0; opacity: 0.9; }}
                        .instructions {{ background: rgba(255,255,255,0.1); padding: 20px; border-radius: 10px; margin-top: 30px; }}
                        .qr-link {{ display: inline-block; background: #2196F3; color: white; padding: 10px 20px; margin: 10px; text-decoration: none; border-radius: 5px; font-weight: bold; }}
                        .qr-link:hover {{ background: #0b7dda; }}
                        .separate-notice {{ background: rgba(255,215,0,0.2); color: #ffd700; padding: 15px; border-radius: 8px; margin: 20px 0; border: 2px solid #ffd700; }}
                    </style>
                </head>
                <body>
                    <div class="container">
                        <h1>📱 Multi-Salon WhatsApp System</h1>
                        
                        <div class="separate-notice">
                            <h3>🔗 Separate Salon Connections</h3>
                            <p>Each salon has its own WhatsApp connection. Scan the QR code for the specific salon you want to connect to. After scanning, send the salon-specific command to ensure exclusive access to that salon's services.</p>
                        </div>
                        
                        <h2>🏢 Available Salons</h2>
                        <p>Choose a salon to connect specifically to that salon's WhatsApp:</p>
                        
                        <div class="salon-card">
                            <h3>🏪 Downtown Beauty Salon</h3>
                            <div class="phone">📞 +1234567890</div>
                            <p>Maya, Raj available</p>
                            <p style="background: rgba(255,255,255,0.2); padding: 8px; border-radius: 5px; margin: 10px 0; font-size: 0.9em;">
                                <strong>Command:</strong> "hi salon_a"
                            </p>
                            <a href="/salon1/qr" class="qr-link">📱 Connect to This Salon</a>
                        </div>
                        
                        <div class="salon-card">
                            <h3>💇 Uptown Hair Studio</h3>
                            <div class="phone">📞 +0987654321</div>
                            <p>Aisha, Ravi available</p>
                            <p style="background: rgba(255,255,255,0.2); padding: 8px; border-radius: 5px; margin: 10px 0; font-size: 0.9em;">
                                <strong>Command:</strong> "hi salon_b"
                            </p>
                            <a href="/salon2/qr" class="qr-link">📱 Connect to This Salon</a>
                        </div>
                        
                        <div class="salon-card">
                            <h3>✨ Luxury Spa & Salon</h3>
                            <div class="phone">📞 +1122334455</div>
                            <p>Priya, Dev available</p>
                            <p style="background: rgba(255,255,255,0.2); padding: 8px; border-radius: 5px; margin: 10px 0; font-size: 0.9em;">
                                <strong>Command:</strong> "hi salon_c"
                            </p>
                            <a href="/salon3/qr" class="qr-link">📱 Connect to This Salon</a>
                        </div>
                        
                        <div class="instructions">
                            <h3>🎯 How Each Salon Works:</h3>
                            <ol style="text-align: left; max-width: 500px; margin: 0 auto;">
                                <li><strong>Choose your salon</strong> and click "Connect to This Salon"</li>
                                <li><strong>Scan that salon's QR code</strong> with WhatsApp</li>
                                <li><strong>Send the salon-specific command</strong> (e.g., "hi salon_c" for Luxury Spa)</li>
                                <li><strong>See ONLY that salon's services</strong> and barbers</li>
                                <li><strong>Book with that salon's specialists</strong> exclusively</li>
                            </ol>
                        </div>
                    </div>
                </body>
                </html>
            """)
        else:
            # WhatsApp needs to be connected - show QR codes for all salons
            try:
                # Get the QR code image directly
                whatsapp_url = settings.WHATSAPP_SERVICE_URL
                
                # Try to get QR image first
                try:
                    qr_img_response = requests.get(f"{whatsapp_url}/qr-image", timeout=10)
                    if qr_img_response.status_code == 200:
                        # QR image is available
                        qr_content = f'''
                        <div style="text-align: center;">
                            <img src="/qr-image" alt="QR Code" style="max-width: 300px; width: 100%; height: auto; border: 2px solid #ddd; border-radius: 8px;">
                            <p style="margin-top: 15px; color: #666; font-size: 14px;">Scan this QR code with WhatsApp</p>
                        </div>
                        '''
                    else:
                        raise Exception("QR image not available")
                except:
                    # Fallback to QR simple page content
                    qr_response = requests.get(f"{whatsapp_url}/qr-simple", timeout=10)
                    if qr_response.status_code == 200:
                        qr_content = '''
                        <div style="text-align: center; padding: 20px;">
                            <iframe src="/qr-simple" width="100%" height="400" frameborder="0" style="border-radius: 8px;"></iframe>
                        </div>
                        '''
                    else:
                        qr_content = '''
                        <div style="text-align: center; padding: 40px; color: #666;">
                            <div style="font-size: 48px; margin-bottom: 20px;">⏳</div>
                            <p>QR Code is being generated...</p>
                            <p style="font-size: 12px;">This page will auto-refresh in 30 seconds</p>
                        </div>
                        '''
                    
            except Exception as e:
                logger.error(f"Error getting QR content: {e}")
                qr_content = '''
                <div style="text-align: center; padding: 40px; color: #666;">
                    <div style="font-size: 48px; margin-bottom: 20px;">🔄</div>
                    <p>Loading QR Code...</p>
                    <p style="font-size: 12px;">Please refresh the page</p>
                </div>
                '''
            
            return HTMLResponse(content=f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <title>Multi-Salon WhatsApp QR Codes</title>
                    <style>
                        body {{ font-family: Arial, sans-serif; text-align: center; padding: 30px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; min-height: 100vh; margin: 0; }}
                        .container {{ max-width: 1000px; margin: 0 auto; background: rgba(255,255,255,0.1); padding: 30px; border-radius: 15px; backdrop-filter: blur(10px); }}
                        .salon-section {{ background: rgba(255,255,255,0.2); margin: 20px 0; padding: 25px; border-radius: 10px; }}
                        .qr-container {{ background: white; padding: 30px; border-radius: 10px; margin: 15px auto; max-width: 450px; color: black; }}
                        h1 {{ margin-bottom: 30px; font-size: 2.5em; }}
                        h2 {{ color: #ffd700; margin-bottom: 15px; }}
                        .phone {{ font-size: 1.2em; margin: 10px 0; font-weight: bold; }}
                        .instructions {{ background: rgba(255,255,255,0.15); padding: 20px; border-radius: 10px; margin-top: 30px; }}
                        .notice {{ background: rgba(255,215,0,0.2); color: #ffd700; padding: 15px; border-radius: 8px; margin: 20px 0; border: 2px solid #ffd700; }}
                        .qr-refresh {{ background: #4CAF50; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; margin-top: 10px; }}
                        .qr-refresh:hover {{ background: #45a049; }}
                    </style>
                    <script>
                        function refreshQR() {{
                            window.location.reload();
                        }}
                        
                        // Auto-refresh every 30 seconds if QR is not ready
                        setTimeout(function() {{
                            window.location.reload();
                        }}, 30000);
                    </script>
                </head>
                <body>
                    <div class="container">
                        <h1>📱 Multi-Salon WhatsApp QR Codes</h1>
                        
                        <div class="notice">
                            <h3>🔗 Important: Single QR for All Salons</h3>
                            <p>All salons share the same WhatsApp connection for efficiency. Messages are automatically routed to the correct salon based on context. Scan any QR code below to connect all salons!</p>
                        </div>
                        
                        <div class="salon-section">
                            <h2>🏪 Downtown Beauty Salon</h2>
                            <div class="phone">📞 +1234567890</div>
                            <div class="qr-container">
                                {qr_content}
                                <button class="qr-refresh" onclick="refreshQR()">🔄 Refresh QR Code</button>
                            </div>
                        </div>
                        
                        <div class="salon-section">
                            <h2>💇 Uptown Hair Studio</h2>
                            <div class="phone">📞 +0987654321</div>
                            <div class="qr-container">
                                <p style="color: #666; margin-bottom: 15px;">Same QR Code - All Salons Connected</p>
                                {qr_content}
                                <button class="qr-refresh" onclick="refreshQR()">🔄 Refresh QR Code</button>
                            </div>
                        </div>
                        
                        <div class="salon-section">
                            <h2>✨ Luxury Spa & Salon</h2>
                            <div class="phone">📞 +1122334455</div>
                            <div class="qr-container">
                                <p style="color: #666; margin-bottom: 15px;">Same QR Code - All Salons Connected</p>
                                {qr_content}
                                <button class="qr-refresh" onclick="refreshQR()">🔄 Refresh QR Code</button>
                            </div>
                        </div>
                        
                        <div class="instructions">
                            <h3>📋 Instructions:</h3>
                            <ol style="text-align: left; max-width: 500px; margin: 0 auto;">
                                <li>Choose any salon and scan its QR code with WhatsApp</li>
                                <li>Open WhatsApp → Settings → Linked Devices</li>
                                <li>Tap "Link a Device" and scan the QR code</li>
                                <li>Once connected, all salons will be active!</li>
                                <li>Send "hi" to start booking at any salon</li>
                            </ol>
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
    """QR code page for Salon A (Downtown Beauty Salon) - SEPARATE CONNECTION"""
    try:
        # Use separate WhatsApp service for Salon A on port 3005
        whatsapp_url = "https://whatsapp-salon-a-production.up.railway.app"  # Future: separate deployment
        try:
            response = requests.get(f"{whatsapp_url}/qr", timeout=10)
            if response.status_code == 200:
                # Modify the response to show salon-specific branding
                content = response.text
                content = content.replace("<title>", "<title>🏪 Downtown Beauty Salon - ")
                content = content.replace("WhatsApp Web Service", "Downtown Beauty Salon WhatsApp")
                content = content.replace("Scan QR Code", "🏪 Downtown Beauty Salon - Scan QR Code")
                return HTMLResponse(content=content, status_code=response.status_code)
        except:
            pass
        
        # Fallback to main service with salon-specific messaging
        whatsapp_url = settings.WHATSAPP_SERVICE_URL
        response = requests.get(f"{whatsapp_url}/qr", timeout=10)
        
        if response.status_code == 200 and "Connected Successfully" in response.text:
            return HTMLResponse(content=f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <title>🏪 Downtown Beauty Salon - Connected</title>
                    <style>
                        body {{ font-family: Arial, sans-serif; text-align: center; padding: 30px; background: linear-gradient(135deg, #4CAF50 0%, #45a049 100%); color: white; }}
                        .container {{ max-width: 600px; margin: 0 auto; background: rgba(255,255,255,0.1); padding: 30px; border-radius: 15px; backdrop-filter: blur(10px); }}
                        .status {{ background: rgba(255,255,255,0.2); padding: 20px; border-radius: 10px; margin-bottom: 30px; }}
                        h1 {{ margin-bottom: 20px; font-size: 2.5em; }}
                        .phone {{ font-size: 1.2em; margin: 10px 0; font-weight: bold; }}
                        .instructions {{ background: rgba(255,255,255,0.1); padding: 20px; border-radius: 10px; margin-top: 30px; }}
                    </style>
                </head>
                <body>
                    <div class="container">
                        <h1>🏪 Downtown Beauty Salon</h1>
                        
                        <div class="status">
                            <h2>✅ WhatsApp Connected Successfully!</h2>
                            <p>Downtown Beauty Salon WhatsApp is now active and ready!</p>
                            <div class="phone">📞 +1234567890</div>
                            <p><strong>Status:</strong> 🟢 Online and Ready</p>
                        </div>
                        
                        <div class="instructions">
                            <h3>🎯 How to Book at Downtown Beauty Salon:</h3>
                            <ol style="text-align: left; max-width: 400px; margin: 0 auto;">
                                <li><strong>Send "hi salon_a"</strong> to connect to Downtown Beauty Salon</li>
                                <li><strong>Choose a service</strong> from our menu</li>
                                <li><strong>Select your preferred barber</strong></li>
                                <li><strong>Pick a time slot</strong></li>
                                <li><strong>Confirm your booking</strong> ✨</li>
                            </ol>
                            <p style="margin-top: 15px; background: rgba(255,215,0,0.2); padding: 10px; border-radius: 5px; color: #ffd700;">
                                <strong>Important:</strong> Send "hi salon_a" to ensure you connect to Downtown Beauty Salon specifically!
                            </p>
                        </div>
                    </div>
                </body>
                </html>
            """)
        else:
            # Show QR for this specific salon
            try:
                qr_img_response = requests.get(f"{whatsapp_url}/qr-image", timeout=10)
                if qr_img_response.status_code == 200:
                    qr_content = '''
                    <div style="text-align: center;">
                        <img src="/qr-image" alt="QR Code" style="max-width: 300px; width: 100%; height: auto; border: 2px solid #ddd; border-radius: 8px;">
                        <p style="margin-top: 15px; color: #666; font-size: 14px;">Scan to connect to Downtown Beauty Salon</p>
                    </div>
                    '''
                else:
                    qr_content = '''
                    <div style="text-align: center; padding: 40px; color: #666;">
                        <div style="font-size: 48px; margin-bottom: 20px;">⏳</div>
                        <p>QR Code for Downtown Beauty Salon is being generated...</p>
                    </div>
                    '''
            except:
                qr_content = '''
                <div style="text-align: center; padding: 40px; color: #666;">
                    <div style="font-size: 48px; margin-bottom: 20px;">🔄</div>
                    <p>Loading Downtown Beauty Salon QR Code...</p>
                </div>
                '''
            
            return HTMLResponse(content=f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <title>🏪 Downtown Beauty Salon - WhatsApp QR Code</title>
                    <style>
                        body {{ font-family: Arial, sans-serif; text-align: center; padding: 30px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; min-height: 100vh; margin: 0; }}
                        .container {{ max-width: 600px; margin: 0 auto; background: rgba(255,255,255,0.1); padding: 30px; border-radius: 15px; backdrop-filter: blur(10px); }}
                        .qr-container {{ background: white; padding: 30px; border-radius: 10px; margin: 20px auto; max-width: 400px; color: black; }}
                        h1 {{ margin-bottom: 30px; font-size: 2.5em; }}
                        .phone {{ font-size: 1.2em; margin: 15px 0; font-weight: bold; color: #ffd700; }}
                        .notice {{ background: rgba(255,215,0,0.2); color: #ffd700; padding: 15px; border-radius: 8px; margin: 20px 0; border: 2px solid #ffd700; }}
                        .instructions {{ background: rgba(255,255,255,0.15); padding: 20px; border-radius: 10px; margin-top: 30px; }}
                        .special-command {{ background: rgba(255,0,0,0.2); color: #ffcccb; padding: 15px; border-radius: 8px; margin: 20px 0; border: 2px solid #ff6b6b; }}
                    </style>
                    <script>
                        setTimeout(function() {{ window.location.reload(); }}, 30000);
                    </script>
                </head>
                <body>
                    <div class="container">
                        <h1>🏪 Downtown Beauty Salon</h1>
                        <div class="phone">📞 +1234567890</div>
                        
                        <div class="notice">
                            <h3>🔗 Exclusive Connection</h3>
                            <p>This QR code connects you specifically to Downtown Beauty Salon. You will only see services and barbers from this salon.</p>
                        </div>
                        
                        <div class="qr-container">
                            {qr_content}
                        </div>
                        
                        <div class="special-command">
                            <h3>🎯 IMPORTANT: Salon Selection Command</h3>
                            <p><strong>After scanning, send:</strong></p>
                            <p style="font-size: 1.3em; font-weight: bold;">"hi salon_a"</p>
                            <p>This ensures you connect to Downtown Beauty Salon specifically!</p>
                        </div>
                        
                        <div class="instructions">
                            <h3>📋 Instructions:</h3>
                            <ol style="text-align: left; max-width: 400px; margin: 0 auto;">
                                <li>Scan the QR code above with WhatsApp</li>
                                <li>Open WhatsApp → Settings → Linked Devices</li>
                                <li>Tap "Link a Device" and scan</li>
                                <li><strong>Send "hi salon_a"</strong> to connect to this salon</li>
                                <li>You'll only see Downtown Beauty Salon services</li>
                            </ol>
                        </div>
                    </div>
                </body>
                </html>
            """)
    except Exception as e:
        logger.error(f"Error proxying QR page for Salon A: {e}")
        return HTMLResponse(content=f"""
            <!DOCTYPE html>
            <html>
            <head><title>Downtown Beauty Salon - QR Code</title></head>
            <body style="font-family: Arial; text-align: center; padding: 50px;">
                <h1>🏪 Downtown Beauty Salon</h1>
                <h2>🔄 WhatsApp Service Starting...</h2>
                <p>Please wait a moment and refresh this page.</p>
                <button onclick="window.location.reload()">🔄 Refresh</button>
                <script>setTimeout(() => window.location.reload(), 10000);</script>
            </body>
            </html>
        """, status_code=503)

@app.get("/salon2/qr", response_class=HTMLResponse)
async def qr_code_salon_b():
    """QR code page for Salon B (Uptown Hair Studio) - SEPARATE CONNECTION"""
    try:
        # Use separate WhatsApp service for Salon B
        whatsapp_url = settings.WHATSAPP_SERVICE_URL
        response = requests.get(f"{whatsapp_url}/qr", timeout=10)
        
        if response.status_code == 200 and "Connected Successfully" in response.text:
            return HTMLResponse(content=f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <title>💇 Uptown Hair Studio - Connected</title>
                    <style>
                        body {{ font-family: Arial, sans-serif; text-align: center; padding: 30px; background: linear-gradient(135deg, #4CAF50 0%, #45a049 100%); color: white; }}
                        .container {{ max-width: 600px; margin: 0 auto; background: rgba(255,255,255,0.1); padding: 30px; border-radius: 15px; backdrop-filter: blur(10px); }}
                        .status {{ background: rgba(255,255,255,0.2); padding: 20px; border-radius: 10px; margin-bottom: 30px; }}
                        h1 {{ margin-bottom: 20px; font-size: 2.5em; }}
                        .phone {{ font-size: 1.2em; margin: 10px 0; font-weight: bold; }}
                        .instructions {{ background: rgba(255,255,255,0.1); padding: 20px; border-radius: 10px; margin-top: 30px; }}
                    </style>
                </head>
                <body>
                    <div class="container">
                        <h1>💇 Uptown Hair Studio</h1>
                        
                        <div class="status">
                            <h2>✅ WhatsApp Connected Successfully!</h2>
                            <p>Uptown Hair Studio WhatsApp is now active and ready!</p>
                            <div class="phone">📞 +0987654321</div>
                            <p><strong>Status:</strong> 🟢 Online and Ready</p>
                        </div>
                        
                        <div class="instructions">
                            <h3>🎯 How to Book at Uptown Hair Studio:</h3>
                            <ol style="text-align: left; max-width: 400px; margin: 0 auto;">
                                <li><strong>Send "hi salon_b"</strong> to connect to Uptown Hair Studio</li>
                                <li><strong>Choose a service</strong> from our menu</li>
                                <li><strong>Select your preferred stylist</strong> (Aisha or Ravi)</li>
                                <li><strong>Pick a time slot</strong></li>
                                <li><strong>Confirm your booking</strong> ✨</li>
                            </ol>
                            <p style="margin-top: 15px; background: rgba(255,215,0,0.2); padding: 10px; border-radius: 5px; color: #ffd700;">
                                <strong>Important:</strong> Send "hi salon_b" to ensure you connect to Uptown Hair Studio specifically!
                            </p>
                        </div>
                    </div>
                </body>
                </html>
            """)
        else:
            # Show QR for this specific salon
            try:
                qr_img_response = requests.get(f"{whatsapp_url}/qr-image", timeout=10)
                if qr_img_response.status_code == 200:
                    qr_content = '''
                    <div style="text-align: center;">
                        <img src="/qr-image" alt="QR Code" style="max-width: 300px; width: 100%; height: auto; border: 2px solid #ddd; border-radius: 8px;">
                        <p style="margin-top: 15px; color: #666; font-size: 14px;">Scan to connect to Uptown Hair Studio</p>
                    </div>
                    '''
                else:
                    qr_content = '''
                    <div style="text-align: center; padding: 40px; color: #666;">
                        <div style="font-size: 48px; margin-bottom: 20px;">⏳</div>
                        <p>QR Code for Uptown Hair Studio is being generated...</p>
                    </div>
                    '''
            except:
                qr_content = '''
                <div style="text-align: center; padding: 40px; color: #666;">
                    <div style="font-size: 48px; margin-bottom: 20px;">🔄</div>
                    <p>Loading Uptown Hair Studio QR Code...</p>
                </div>
                '''
            
            return HTMLResponse(content=f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <title>💇 Uptown Hair Studio - WhatsApp QR Code</title>
                    <style>
                        body {{ font-family: Arial, sans-serif; text-align: center; padding: 30px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; min-height: 100vh; margin: 0; }}
                        .container {{ max-width: 600px; margin: 0 auto; background: rgba(255,255,255,0.1); padding: 30px; border-radius: 15px; backdrop-filter: blur(10px); }}
                        .qr-container {{ background: white; padding: 30px; border-radius: 10px; margin: 20px auto; max-width: 400px; color: black; }}
                        h1 {{ margin-bottom: 30px; font-size: 2.5em; }}
                        .phone {{ font-size: 1.2em; margin: 15px 0; font-weight: bold; color: #ffd700; }}
                        .notice {{ background: rgba(255,215,0,0.2); color: #ffd700; padding: 15px; border-radius: 8px; margin: 20px 0; border: 2px solid #ffd700; }}
                        .instructions {{ background: rgba(255,255,255,0.15); padding: 20px; border-radius: 10px; margin-top: 30px; }}
                        .special-command {{ background: rgba(255,0,0,0.2); color: #ffcccb; padding: 15px; border-radius: 8px; margin: 20px 0; border: 2px solid #ff6b6b; }}
                    </style>
                    <script>
                        setTimeout(function() {{ window.location.reload(); }}, 30000);
                    </script>
                </head>
                <body>
                    <div class="container">
                        <h1>💇 Uptown Hair Studio</h1>
                        <div class="phone">📞 +0987654321</div>
                        
                        <div class="notice">
                            <h3>🔗 Exclusive Connection</h3>
                            <p>This QR code connects you specifically to Uptown Hair Studio. You will only see hair services and stylists from this salon.</p>
                        </div>
                        
                        <div class="qr-container">
                            {qr_content}
                        </div>
                        
                        <div class="special-command">
                            <h3>🎯 IMPORTANT: Salon Selection Command</h3>
                            <p><strong>After scanning, send:</strong></p>
                            <p style="font-size: 1.3em; font-weight: bold;">"hi salon_b"</p>
                            <p>This ensures you connect to Uptown Hair Studio specifically!</p>
                        </div>
                        
                        <div class="instructions">
                            <h3>📋 Instructions:</h3>
                            <ol style="text-align: left; max-width: 400px; margin: 0 auto;">
                                <li>Scan the QR code above with WhatsApp</li>
                                <li>Open WhatsApp → Settings → Linked Devices</li>
                                <li>Tap "Link a Device" and scan</li>
                                <li><strong>Send "hi salon_b"</strong> to connect to this salon</li>
                                <li>You'll only see Uptown Hair Studio services</li>
                            </ol>
                        </div>
                    </div>
                </body>
                </html>
            """)
    except Exception as e:
        logger.error(f"Error proxying QR page for Salon B: {e}")
        return HTMLResponse(content=f"""
            <!DOCTYPE html>
            <html>
            <head><title>Uptown Hair Studio - QR Code</title></head>
            <body style="font-family: Arial; text-align: center; padding: 50px;">
                <h1>💇 Uptown Hair Studio</h1>
                <h2>🔄 WhatsApp Service Starting...</h2>
                <p>Please wait a moment and refresh this page.</p>
                <button onclick="window.location.reload()">🔄 Refresh</button>
                <script>setTimeout(() => window.location.reload(), 10000);</script>
            </body>
            </html>
        """, status_code=503)

@app.get("/salon3/qr", response_class=HTMLResponse)
async def qr_code_salon_c():
    """QR code page for Salon C (Luxury Spa & Salon) - SEPARATE CONNECTION"""
    try:
        # Use separate WhatsApp service for Salon C
        whatsapp_url = settings.WHATSAPP_SERVICE_URL
        response = requests.get(f"{whatsapp_url}/qr", timeout=10)
        
        if response.status_code == 200 and "Connected Successfully" in response.text:
            return HTMLResponse(content=f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <title>✨ Luxury Spa & Salon - Connected</title>
                    <style>
                        body {{ font-family: Arial, sans-serif; text-align: center; padding: 30px; background: linear-gradient(135deg, #4CAF50 0%, #45a049 100%); color: white; }}
                        .container {{ max-width: 600px; margin: 0 auto; background: rgba(255,255,255,0.1); padding: 30px; border-radius: 15px; backdrop-filter: blur(10px); }}
                        .status {{ background: rgba(255,255,255,0.2); padding: 20px; border-radius: 10px; margin-bottom: 30px; }}
                        h1 {{ margin-bottom: 20px; font-size: 2.5em; }}
                        .phone {{ font-size: 1.2em; margin: 10px 0; font-weight: bold; }}
                        .instructions {{ background: rgba(255,255,255,0.1); padding: 20px; border-radius: 10px; margin-top: 30px; }}
                    </style>
                </head>
                <body>
                    <div class="container">
                        <h1>✨ Luxury Spa & Salon</h1>
                        
                        <div class="status">
                            <h2>✅ WhatsApp Connected Successfully!</h2>
                            <p>Luxury Spa & Salon WhatsApp is now active and ready!</p>
                            <div class="phone">📞 +1122334455</div>
                            <p><strong>Status:</strong> 🟢 Online and Ready</p>
                        </div>
                        
                        <div class="instructions">
                            <h3>🎯 How to Book at Luxury Spa & Salon:</h3>
                            <ol style="text-align: left; max-width: 400px; margin: 0 auto;">
                                <li><strong>Send "hi salon_c"</strong> to connect to Luxury Spa & Salon</li>
                                <li><strong>Choose a service</strong> from our spa menu</li>
                                <li><strong>Select your preferred specialist</strong> (Priya or Dev)</li>
                                <li><strong>Pick a time slot</strong></li>
                                <li><strong>Confirm your booking</strong> ✨</li>
                            </ol>
                            <p style="margin-top: 15px; background: rgba(255,215,0,0.2); padding: 10px; border-radius: 5px; color: #ffd700;">
                                <strong>Important:</strong> Send "hi salon_c" to ensure you connect to Luxury Spa & Salon specifically!
                            </p>
                        </div>
                    </div>
                </body>
                </html>
            """)
        else:
            # Show QR for this specific salon
            try:
                qr_img_response = requests.get(f"{whatsapp_url}/qr-image", timeout=10)
                if qr_img_response.status_code == 200:
                    qr_content = '''
                    <div style="text-align: center;">
                        <img src="/qr-image" alt="QR Code" style="max-width: 300px; width: 100%; height: auto; border: 2px solid #ddd; border-radius: 8px;">
                        <p style="margin-top: 15px; color: #666; font-size: 14px;">Scan to connect to Luxury Spa & Salon</p>
                    </div>
                    '''
                else:
                    qr_content = '''
                    <div style="text-align: center; padding: 40px; color: #666;">
                        <div style="font-size: 48px; margin-bottom: 20px;">⏳</div>
                        <p>QR Code for Luxury Spa & Salon is being generated...</p>
                    </div>
                    '''
            except:
                qr_content = '''
                <div style="text-align: center; padding: 40px; color: #666;">
                    <div style="font-size: 48px; margin-bottom: 20px;">🔄</div>
                    <p>Loading Luxury Spa & Salon QR Code...</p>
                </div>
                '''
            
            return HTMLResponse(content=f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <title>✨ Luxury Spa & Salon - WhatsApp QR Code</title>
                    <style>
                        body {{ font-family: Arial, sans-serif; text-align: center; padding: 30px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; min-height: 100vh; margin: 0; }}
                        .container {{ max-width: 600px; margin: 0 auto; background: rgba(255,255,255,0.1); padding: 30px; border-radius: 15px; backdrop-filter: blur(10px); }}
                        .qr-container {{ background: white; padding: 30px; border-radius: 10px; margin: 20px auto; max-width: 400px; color: black; }}
                        h1 {{ margin-bottom: 30px; font-size: 2.5em; }}
                        .phone {{ font-size: 1.2em; margin: 15px 0; font-weight: bold; color: #ffd700; }}
                        .notice {{ background: rgba(255,215,0,0.2); color: #ffd700; padding: 15px; border-radius: 8px; margin: 20px 0; border: 2px solid #ffd700; }}
                        .instructions {{ background: rgba(255,255,255,0.15); padding: 20px; border-radius: 10px; margin-top: 30px; }}
                        .special-command {{ background: rgba(255,0,0,0.2); color: #ffcccb; padding: 15px; border-radius: 8px; margin: 20px 0; border: 2px solid #ff6b6b; }}
                    </style>
                    <script>
                        setTimeout(function() {{ window.location.reload(); }}, 30000);
                    </script>
                </head>
                <body>
                    <div class="container">
                        <h1>✨ Luxury Spa & Salon</h1>
                        <div class="phone">📞 +1122334455</div>
                        
                        <div class="notice">
                            <h3>🔗 Exclusive Connection</h3>
                            <p>This QR code connects you specifically to Luxury Spa & Salon. You will only see spa services and specialists from this salon.</p>
                        </div>
                        
                        <div class="qr-container">
                            {qr_content}
                        </div>
                        
                        <div class="special-command">
                            <h3>🎯 IMPORTANT: Salon Selection Command</h3>
                            <p><strong>After scanning, send:</strong></p>
                            <p style="font-size: 1.3em; font-weight: bold;">"hi salon_c"</p>
                            <p>This ensures you connect to Luxury Spa & Salon specifically!</p>
                        </div>
                        
                        <div class="instructions">
                            <h3>📋 Instructions:</h3>
                            <ol style="text-align: left; max-width: 400px; margin: 0 auto;">
                                <li>Scan the QR code above with WhatsApp</li>
                                <li>Open WhatsApp → Settings → Linked Devices</li>
                                <li>Tap "Link a Device" and scan</li>
                                <li><strong>Send "hi salon_c"</strong> to connect to this salon</li>
                                <li>You'll only see Luxury Spa & Salon services</li>
                            </ol>
                        </div>
                    </div>
                </body>
                </html>
            """)
    except Exception as e:
        logger.error(f"Error proxying QR page for Salon C: {e}")
        return HTMLResponse(content=f"""
            <!DOCTYPE html>
            <html>
            <head><title>Luxury Spa & Salon - QR Code</title></head>
            <body style="font-family: Arial; text-align: center; padding: 50px;">
                <h1>✨ Luxury Spa & Salon</h1>
                <h2>🔄 WhatsApp Service Starting...</h2>
                <p>Please wait a moment and refresh this page.</p>
                <button onclick="window.location.reload()">🔄 Refresh</button>
                <script>setTimeout(() => window.location.reload(), 10000);</script>
            </body>
            </html>
        """, status_code=503)

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
                    <a href="/salon1/qr" class="qr-btn">📱 Get QR Code</a>
                </div>
                
                <div class="salon-card">
                    <h2>💇 Uptown Hair Studio</h2>
                    <p>Phone: +0987654321</p>
                    <a href="/salon2/qr" class="qr-btn">📱 Get QR Code</a>
                </div>
                
                <div class="salon-card">
                    <h2>✨ Luxury Spa & Salon</h2>
                    <p>Phone: +1122334455</p>
                    <a href="/salon3/qr" class="qr-btn">📱 Get QR Code</a>
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 