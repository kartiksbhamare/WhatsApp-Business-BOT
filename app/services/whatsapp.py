import requests
from datetime import datetime
import logging
from app.config import get_settings
from typing import Dict, Optional

logger = logging.getLogger(__name__)
settings = get_settings()

def send_whatsapp_message(to_number: str, message: str) -> bool:
    """
    Send a WhatsApp message using WhatsApp Web service
    
    Args:
        to_number: Recipient's phone number (with or without country code)
        message: Message text to send
        
    Returns:
        bool: True if message was sent successfully
    """
    try:
        # Clean the phone number - remove any 'whatsapp:' prefix if present
        phone_number = to_number.replace("whatsapp:", "").strip()
        
        # Make request to WhatsApp Web service
        response = requests.post(
            f"{settings.WHATSAPP_SERVICE_URL}/send-message",
            json={
                "phone": phone_number,
                "message": message
            },
            timeout=10
        )
        
        if response.status_code == 200:
            logger.info(f"Message sent successfully to {phone_number}")
            return True
        else:
            logger.error(f"Failed to send message. Status: {response.status_code}, Response: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Network error sending message: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Error sending message: {str(e)}")
        return False

def send_confirmation(phone: str, barber: str, time_slot: str, service: str) -> bool:
    """
    Send a WhatsApp confirmation message using WhatsApp Web service
    
    Args:
        phone: Customer's phone number
        barber: Barber's name
        time_slot: ISO format datetime string
        service: Service type
        
    Returns:
        bool: True if message was sent successfully
    """
    try:
        # Format the time slot
        booking_time = datetime.fromisoformat(time_slot)
        formatted_time = booking_time.strftime("%I:%M %p on %B %d, %Y")
        
        # Compose the message
        message = (
            f"✨ Booking Confirmed! ✨\n\n"
            f"Thank you for booking with us!\n\n"
            f"📅 Appointment Details:\n"
            f"• Service: {service}\n"
            f"• Barber: {barber}\n"
            f"• Time: {formatted_time}\n\n"
            f"See you soon! Reply 'CANCEL' to cancel your appointment."
        )
        
        return send_whatsapp_message(phone, message)
        
    except Exception as e:
        logger.error(f"Error sending confirmation: {str(e)}")
        return False

def check_whatsapp_service_health() -> bool:
    """Check if WhatsApp Web service is healthy"""
    try:
        response = requests.get(f'{settings.WHATSAPP_SERVICE_URL}/health', timeout=5)
        return response.status_code == 200
    except Exception as e:
        logger.warning(f"WhatsApp service health check failed: {e}")
        return False

def get_whatsapp_service_info() -> Optional[Dict]:
    """Get WhatsApp service information"""
    try:
        response = requests.get(f'{settings.WHATSAPP_SERVICE_URL}/info', timeout=5)
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        logger.warning(f"Failed to get WhatsApp service info: {e}")
        return None 