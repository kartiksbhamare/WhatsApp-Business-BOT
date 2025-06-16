from fastapi import FastAPI, Request, HTTPException, Form, Response
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Optional
from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse
from twilio.base.exceptions import TwilioRestException
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
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Initialize Twilio client
try:
    twilio_client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
    logger.info("Twilio client initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize Twilio client: {str(e)}")
    twilio_client = None

app = FastAPI(
    title="Smart WhatsApp Booking Bot",
    description="A WhatsApp-based booking system for salons using FastAPI and Firebase",
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

def send_whatsapp_message(to_number: str, message: str) -> bool:
    """Send a WhatsApp message using Twilio client"""
    if not twilio_client:
        logger.error("Twilio client not initialized")
        return False
        
    try:
        # Clean the phone number
        to_number = to_number.replace("whatsapp:", "")
        
        # Send message
        message = twilio_client.messages.create(
            body=message,
            from_=f"whatsapp:{settings.TWILIO_PHONE_NUMBER}",
            to=f"whatsapp:{to_number}"
        )
        logger.info(f"Message sent successfully. SID: {message.sid}")
        return True
    except TwilioRestException as e:
        # Check specifically for the daily limit error
        if "exceeded the 9 daily messages limit" in str(e):
            logger.error("⚠️ DAILY MESSAGE LIMIT EXCEEDED: Your Twilio trial account has reached its 9 message daily limit. Please wait for the limit to reset or upgrade your account.")
        else:
            logger.error(f"Twilio error sending message: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Error sending message: {str(e)}")
        return False

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
    
    # Initialize database
    init_default_data()

@app.get("/")
async def root():
    """Health check endpoint"""
    return {"status": "healthy", "message": "Smart WhatsApp Booking Bot is running"}

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

@app.post("/webhook")
async def webhook(request: Request):
    try:
        logger.info("Received webhook request")
        
        # Get form data
        form_data = await request.form()
        form_dict = dict(form_data)
        logger.info(f"Form data: {form_dict}")
        
        # Extract message and phone
        message = form_dict.get("Body", "").lower() if form_dict else ""
        phone = form_dict.get("From", "").replace("whatsapp:", "") if form_dict else ""
        
        if not message:
            logger.error("No message found in request")
            raise HTTPException(status_code=400, detail="No message provided")
            
        logger.info(f"Processing message: '{message}' from phone: {phone}")
        
        # Get session data
        session = get_session_data(phone)
        logger.info(f"Session state: {session}")
        
        # Create TwiML response
        resp = MessagingResponse()
        
        try:
            # Handle message based on session state
            if message in ["hi", "hello", "start", "restart"]:
                if message in ["restart", "start"]:
                    clear_session(phone)
                    session = get_session_data(phone)
                services = get_all_services()
                service_list = "\n".join([f"{s.id}. {s.name} (${s.price}, {s.duration} mins)" for s in services])
                response_text = f"Welcome to our Salon! Here are our services:\n\n{service_list}\n\nPlease enter the number of the service you'd like to book."
                resp.message(response_text)
                logger.info(f"Sending TwiML response: {response_text}")
            
            elif session["step"] == "service" and message.isdigit():
                service = get_service(message)
                if service:
                    barbers = get_barbers_for_service(service.id)
                    if not barbers:
                        resp.message("Sorry, no barbers are currently available for this service.")
                    else:
                        session["service"] = service.id
                        session["step"] = "barber"
                        barber_list = "\n".join([f"{i+1}. {b.name}" for i, b in enumerate(barbers)])
                        resp.message(f"You've selected {service.name}. Please choose your preferred stylist:\n\n{barber_list}")
                else:
                    services = get_all_services()
                    service_list = "\n".join([f"{s.id}. {s.name} (${s.price}, {s.duration} mins)" for s in services])
                    resp.message(f"Invalid service number. Please choose from:\n\n{service_list}")
                
            elif session["step"] == "barber" and message.isdigit():
                try:
                    barbers = get_barbers_for_service(session["service"])
                    selected_barber = barbers[int(message) - 1]
                    session["barber"] = selected_barber.name
                    session["step"] = "time"
                    
                    slots = get_available_slots(selected_barber.name)
                    if not slots:
                        resp.message("Sorry, no available slots found for today. Please try again tomorrow.")
                        clear_session(phone)
                    else:
                        slot_list = "\n".join([f"{i+1}. {slot}" for i, slot in enumerate(slots)])
                        resp.message(f"Please choose your preferred time:\n\n{slot_list}")
                except (IndexError, ValueError):
                    resp.message("Invalid selection. Please choose a valid number.")
                except Exception as e:
                    logger.error(f"Error getting slots: {str(e)}")
                    resp.message("Sorry, there was an error. Please try again.")
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
                        resp.message(f"✨ Booking Confirmed! ✨\n\nService: {service.name}\nBarber: {session['barber']}\nTime: {selected_time}\n\nSee you soon!")
                    else:
                        resp.message("Sorry, that slot is no longer available. Please try again.")
                    clear_session(phone)
                except (IndexError, ValueError):
                    resp.message("Invalid selection. Please choose a valid number.")
                except Exception as e:
                    logger.error(f"Error booking slot: {str(e)}")
                    resp.message("Sorry, there was an error. Please try again.")
                    clear_session(phone)
            
            else:
                resp.message("I don't understand. Please say 'hi' to start booking or 'restart' to start over.")
            
            # Try direct message first using Twilio client
            try:
                # Get the message text from the TwiML response
                message_text = str(resp).split('<Message>')[1].split('</Message>')[0] if '<Message>' in str(resp) else ""
                if message_text:
                    sent = send_whatsapp_message(phone, message_text)
                    if sent:
                        logger.info("Message sent successfully via Twilio client")
                        return Response(content="Message sent", media_type="text/plain")
                    else:
                        logger.warning("Failed to send via Twilio client, falling back to TwiML")
                else:
                    logger.warning("No message to send, falling back to TwiML")
            except TwilioRestException as e:
                if "exceeded the 9 daily messages limit" in str(e):
                    logger.error("⚠️ DAILY MESSAGE LIMIT EXCEEDED: Your Twilio trial account has reached its 9 message daily limit. Please wait for the limit to reset or upgrade your account.")
                else:
                    logger.error(f"Twilio error: {str(e)}")
                logger.info("Falling back to TwiML response")
            except Exception as e:
                logger.warning(f"Error trying direct message: {str(e)}, falling back to TwiML")
            
            # Return TwiML response as fallback
            twiml_response = str(resp)
            logger.info(f"Sending TwiML response: {twiml_response}")
            
            # Check if we're in trial mode
            if "trial" in settings.TWILIO_ACCOUNT_SID.lower():
                logger.warning("⚠️ Using Twilio trial account - messages may be limited")
            
            return Response(content=twiml_response, media_type="application/xml")
            
        except TwilioRestException as e:
            error_msg = str(e)
            if "exceeded the 9 daily messages limit" in error_msg:
                logger.error("⚠️ DAILY MESSAGE LIMIT EXCEEDED: Your Twilio trial account has reached its 9 message daily limit. Please wait for the limit to reset or upgrade your account.")
            else:
                logger.error(f"Twilio error: {error_msg}")
            # Still return a basic response to acknowledge webhook
            return Response(content="Message limit exceeded", media_type="text/plain")
            
    except Exception as e:
        logger.error(f"Error in webhook: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 