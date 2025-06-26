from app.services.firestore_simple import (
    init_default_data,
    get_all_services,
    get_all_barbers,
    get_service,
    get_barbers_for_service,
    get_available_slots,
    book_slot
)
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from typing import Dict
from datetime import datetime, timedelta
import logging

from app.services.whatsapp import check_whatsapp_service_health
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

app = FastAPI(
    title="WhatsApp Booking Bot",
    description="A simple WhatsApp-based booking system",
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

# In-memory session storage
sessions = {}

def get_session_data(phone: str) -> Dict:
    """Get or create session data for a phone number"""
    if phone not in sessions:
        sessions[phone] = {
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

async def process_message(message: str, phone: str, contact_name: str) -> str:
    """Process message and return reply"""
    session = get_session_data(phone)
    session["contact_name"] = contact_name
    
    reply_message = ""
    
    try:
        # Handle message based on session state
        if message in ["hi", "hello", "start", "restart"]:
            logger.info(f"🎯 Handling greeting message: {message}")
            
            if message in ["restart", "start"]:
                clear_session(phone)
                session = get_session_data(phone)
                session["contact_name"] = contact_name
            
            # Get services
            services = get_all_services()
            
            if not services:
                reply_message = f"👋 Welcome to our salon! ✨\n\n😔 Sorry, no services are currently available. Please contact us directly."
            else:
                service_list = "\n".join([f"{i+1}. {s.name} (💰${s.price}, ⏱️{s.duration} mins)" for i, s in enumerate(services)])
                reply_message = f"👋 Welcome to our salon! ✨\n\nHere are our services:\n\n{service_list}\n\n📝 Please enter the number of the service you'd like to book."
        
        elif session["step"] == "service" and message.isdigit():
            logger.info(f"🔢 Processing service selection: {message}")
            services = get_all_services()
            
            try:
                service_index = int(message) - 1
                if 0 <= service_index < len(services):
                    selected_service = services[service_index]
                    barbers = get_barbers_for_service(selected_service.id)
                    
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
            logger.info(f"✂️ Processing barber selection: {message}")
            try:
                barbers = get_barbers_for_service(session["service"])
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
            logger.info(f"📅 Processing date selection: {message}")
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
                
                # Get available slots for the selected date
                slots = get_available_slots(session["barber"], selected_date)
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
            logger.info(f"⏰ Processing time selection: {message}")
            try:
                selected_date = datetime.strptime(session["date"], "%Y-%m-%d")
                slots = get_available_slots(session["barber"], selected_date)
                slot_index = int(message) - 1
                
                if 0 <= slot_index < len(slots):
                    selected_time = slots[slot_index]
                    
                    service = get_service(session["service"])
                    booking_data = {
                        "service_id": service.id,
                        "service_name": service.name,
                        "barber_name": session["barber"],
                        "time_slot": selected_time,
                        "phone": phone,
                        "date": session["date"],
                        "contact_name": session.get("contact_name", contact_name)
                    }
                    
                    result = book_slot(booking_data)
                    if result["status"] == "success":
                        # Format the date for display
                        booking_date = datetime.strptime(session["date"], "%Y-%m-%d")
                        date_display = booking_date.strftime("%A, %B %d, %Y")
                        client_name = session.get("contact_name", "")
                        name_greeting = f"Hi {client_name}! " if client_name and client_name != "Unknown" else ""
                        
                        reply_message = f"🎉✨ Booking Confirmed! ✨🎉\n\n{name_greeting}📋 Your Appointment Details:\n💄 Service: {service.name}\n✂️ Barber: {session['barber']}\n📅 Date: {date_display}\n⏰ Time: {selected_time}\n\n🤗 We look forward to seeing you! Thank you for choosing our salon! 💖"
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
            logger.info(f"❓ Unrecognized message: {message}")
            reply_message = f"🤔 I don't understand that message.\n\n💬 Please say 'hi' to start booking or 'restart' to start over.\n\n🆘 Need help? Just say 'hi'!"
        
        return reply_message
        
    except Exception as e:
        logger.error(f"❌ Error processing message: {str(e)}")
        return "😔 Sorry, there was an error processing your message. Please try again or say 'hi' to start over."

@app.on_event("startup")
async def startup_event():
    """Initialize the database with default data if empty"""
    # Initialize database
    init_default_data()

@app.get("/")
async def root():
    """Root endpoint with basic info"""
    whatsapp_status = "ready" if check_whatsapp_service_health() else "not ready"
    return {
        "service": "WhatsApp Booking Bot",
        "status": "running", 
        "message": "WhatsApp Booking Bot is running",
        "whatsapp_service": whatsapp_status,
        "timestamp": datetime.now().isoformat(),
        "qr_endpoint": "/qr",
        "webhook_endpoint": "/webhook/whatsapp"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        whatsapp_healthy = check_whatsapp_service_health()
        
        # Check database connection and Firebase status
        db_healthy = True
        firebase_connected = False
        try:
            # Import Firebase connection status
            from app.services.firestore_simple import is_firebase_connected
            firebase_connected = is_firebase_connected()
            
            # Try to access services
            services = get_all_services()
            db_healthy = True
        except Exception as db_error:
            logger.error(f"Database health check failed: {db_error}")
            db_healthy = False
        
        overall_status = "healthy" if db_healthy else "degraded"
        
        health_data = {
            "status": overall_status,
            "timestamp": datetime.now().isoformat(),
            "service": "WhatsApp Booking Bot",
            "version": "2.0.0",
            "components": {
                "whatsapp_service": "healthy" if whatsapp_healthy else "unhealthy",
                "database": "healthy" if db_healthy else "unhealthy",
                "firebase": "connected" if firebase_connected else "using_fallback",
                "api": "healthy"
            },
            "firebase_status": {
                "connected": firebase_connected,
                "storage_mode": "firebase" if firebase_connected else "in_memory_fallback"
            }
        }
        
        return health_data
        
    except Exception as e:
        logger.error(f"Health check error: {e}")
        raise HTTPException(status_code=503, detail={
            "status": "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        })

@app.get("/firebase-status")
async def firebase_status():
    """Check Firebase connection status and data"""
    try:
        from app.services.firestore_simple import is_firebase_connected, get_firebase_client
        
        firebase_connected = is_firebase_connected()
        client = get_firebase_client()
        
        # Get data counts
        services = get_all_services()
        barbers = get_all_barbers()
        
        try:
            from app.services.firestore_simple import get_all_bookings
            bookings = get_all_bookings()
        except:
            bookings = []
        
        status_data = {
            "firebase_connected": firebase_connected,
            "client_type": "firebase_admin" if client and client != "REST_API" else ("rest_api" if client == "REST_API" else "none"),
            "data_source": "firebase" if firebase_connected else "in_memory_fallback",
            "data_counts": {
                "services": len(services),
                "barbers": len(barbers),
                "bookings": len(bookings)
            },
            "timestamp": datetime.now().isoformat()
        }
        
        if firebase_connected:
            status_data["message"] = "✅ Firebase connected - using cloud database"
        else:
            status_data["message"] = "⚠️ Firebase not connected - no data available (requires Firebase connection)"
        
        return status_data
        
    except Exception as e:
        logger.error(f"Firebase status check error: {e}")
        return {
            "firebase_connected": False,
            "error": str(e),
            "message": "❌ Error checking Firebase status",
            "timestamp": datetime.now().isoformat()
        }

@app.post("/webhook/whatsapp")
async def whatsapp_webhook(request: Request):
    """Main WhatsApp webhook endpoint"""
    try:
        logger.info("🔔 Received WhatsApp webhook request")
        
        # Get JSON data from WhatsApp Web service
        data = await request.json()
        logger.info(f"📨 WhatsApp data received: {data}")
        
        message = data.get("body", "").lower().strip()
        phone = data.get("from", "").replace("@c.us", "").replace("@g.us", "")
        contact_name = data.get("contactName", "Unknown")
        
        logger.info(f"📱 Processing message: '{message}' from phone: {phone}, contact: {contact_name}")
        
        # Skip group messages
        if data.get("isGroupMsg", False) or "@g.us" in data.get("from", ""):
            logger.info("⏭️ Skipping group message")
            return {"reply": None}
        
        if not message or not phone:
            logger.error("❌ Missing message or phone in WhatsApp webhook")
            return {"error": "Missing required data"}
            
        # Process message
        reply_message = await process_message(message, phone, contact_name)
        
        logger.info(f"📤 Sending reply: {reply_message}")
        return {"reply": reply_message}
        
    except Exception as e:
        logger.error(f"❌ Error in WhatsApp webhook: {str(e)}")
        return {
            "status": "error",
            "message": str(e),
            "reply": "😔 Sorry, we're experiencing technical difficulties. Please try again later."
        }

@app.get("/qr", response_class=HTMLResponse)
async def qr_code_page():
    """QR code page that redirects to WhatsApp service"""
    whatsapp_service_url = f"{settings.WHATSAPP_SERVICE_URL}/qr"
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>WhatsApp QR Code</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {{ font-family: Arial, sans-serif; text-align: center; padding: 50px; background: #f0f8ff; }}
            .container {{ background: white; padding: 30px; border-radius: 10px; display: inline-block; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
            .redirect-btn {{ background: #25D366; color: white; border: none; padding: 15px 30px; border-radius: 5px; cursor: pointer; font-size: 16px; }}
            .redirect-btn:hover {{ background: #128C7E; }}
        </style>
        <script>
            // Auto-redirect to WhatsApp service QR page
            window.location.href = '{whatsapp_service_url}';
        </script>
    </head>
    <body>
        <div class="container">
            <h1>🔄 Redirecting to WhatsApp QR Code...</h1>
            <p>If you're not redirected automatically, click the button below:</p>
            <button class="redirect-btn" onclick="window.location.href='{whatsapp_service_url}'">
                📱 Go to QR Code
            </button>
        </div>
    </body>
    </html>
    """

@app.get("/bookings")
async def get_bookings():
    """Get all bookings for debugging"""
    try:
        from app.services.firestore_simple import get_all_bookings
        bookings = get_all_bookings()
        return {
            "status": "success",
            "count": len(bookings),
            "bookings": bookings
        }
    except Exception as e:
        logger.error(f"Error getting bookings: {str(e)}")
        return {
            "status": "error",
            "message": str(e)
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 