from twilio.rest import Client
from datetime import datetime
import os

def send_confirmation(phone: str, barber: str, time_slot: str, service: str) -> bool:
    """
    Send a WhatsApp confirmation message using Twilio
    
    Args:
        phone: Customer's phone number
        barber: Barber's name
        time_slot: ISO format datetime string
        service: Service type
        
    Returns:
        bool: True if message was sent successfully
    """
    try:
        # Initialize Twilio client
        client = Client(
            os.getenv('TWILIO_ACCOUNT_SID'),
            os.getenv('TWILIO_AUTH_TOKEN')
        )
        
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
        
        # Send the message
        message = client.messages.create(
            body=message,
            from_=f"whatsapp:{os.getenv('TWILIO_PHONE_NUMBER')}",
            to=f"whatsapp:{phone}"
        )
        
        return True
        
    except Exception as e:
        print(f"Error sending confirmation: {str(e)}")
        return False 