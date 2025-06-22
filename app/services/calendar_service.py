from google.oauth2 import service_account
from googleapiclient.discovery import build
from datetime import datetime, timedelta
import pytz
from app.config import get_settings
import logging

logger = logging.getLogger(__name__)
settings = get_settings()

def initialize_calendar_service():
    """Initialize Google Calendar service with credentials"""
    try:
        credentials_dict = settings.get_calendar_credentials()
        if not credentials_dict:
            logger.error("No Google Calendar credentials found")
            return None

        # For service accounts, we need specific scopes
        SCOPES = ['https://www.googleapis.com/auth/calendar']
        
        credentials = service_account.Credentials.from_service_account_info(
            credentials_dict,
            scopes=SCOPES
        )
        
        service = build('calendar', 'v3', credentials=credentials)
        logger.info("Google Calendar service initialized successfully")
        return service
    except Exception as e:
        logger.error(f"Error initializing Google Calendar service: {str(e)}")
        return None

calendar_service = initialize_calendar_service()

def get_available_slots(
    barber_email: str = None,  # This parameter is now optional and unused
    date: datetime = None,
    duration_minutes: int = 30
) -> list:
    """
    Get available time slots from the primary calendar
    
    Args:
        barber_email: (Deprecated) Not used anymore as we use primary calendar
        date: Date to check (defaults to today)
        duration_minutes: Duration of the appointment
    
    Returns:
        List of available datetime slots
    """
    if not calendar_service:
        logger.error("Google Calendar service not initialized")
        return []

    try:
        # Use today if no date provided
        if not date:
            date = datetime.now()
        
        # Get timezone
        tz = pytz.timezone(settings.GOOGLE_CALENDAR_TIMEZONE)
        
        # Set up time bounds for the day (9 AM to 5 PM)
        start_time = tz.localize(datetime.combine(date, datetime.strptime("09:00", "%H:%M").time()))
        end_time = tz.localize(datetime.combine(date, datetime.strptime("17:00", "%H:%M").time()))
        
        logger.info(f"Checking availability between {start_time} and {end_time}")
        
        # Get existing events from primary calendar
        events_result = calendar_service.events().list(
            calendarId='primary',  # Always use primary calendar
            timeMin=start_time.isoformat(),
            timeMax=end_time.isoformat(),
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        logger.info(f"Found {len(events)} existing events")
        
        # Generate all possible 30-minute slots
        all_slots = []
        current_slot = start_time
        while current_slot < end_time:
            all_slots.append(current_slot)
            current_slot += timedelta(minutes=30)
        
        # Remove slots that overlap with events
        available_slots = []
        for slot in all_slots:
            slot_end = slot + timedelta(minutes=duration_minutes)
            is_available = True
            
            for event in events:
                event_start = datetime.fromisoformat(event['start'].get('dateTime', event['start'].get('date')))
                event_end = datetime.fromisoformat(event['end'].get('dateTime', event['end'].get('date')))
                
                # Check if slot overlaps with event
                if not (slot_end <= event_start or slot >= event_end):
                    is_available = False
                    break
            
            if is_available:
                available_slots.append(slot.strftime("%I:%M %p"))  # Format as "HH:MM AM/PM"
        
        logger.info(f"Found {len(available_slots)} available slots")
        return available_slots
        
    except Exception as e:
        logger.error(f"Error getting available slots: {str(e)}")
        return []

def create_calendar_event(
    summary: str,
    start_time: datetime,
    duration_minutes: int,
    description: str = "",
    attendees: list = None,
    timezone: str = None
) -> dict:
    """
    Create a Google Calendar event
    
    Args:
        summary: Event title
        start_time: Event start time (datetime)
        duration_minutes: Duration in minutes
        description: Event description
        attendees: List of email addresses
        timezone: Timezone for the event (defaults to settings)
    
    Returns:
        Dict with status and event details
    """
    if not calendar_service:
        logger.error("Google Calendar service not initialized. Please check credentials.")
        return {
            'status': 'error',
            'message': 'Calendar service not initialized'
        }

    try:
        # Use provided timezone or default from settings
        tz = timezone or settings.GOOGLE_CALENDAR_TIMEZONE
        timezone = pytz.timezone(tz)
        
        # Convert start_time to timezone if it's naive
        if start_time.tzinfo is None:
            start_time = timezone.localize(start_time)
        
        # Calculate end time
        end_time = start_time + timedelta(minutes=duration_minutes)
        
        # Prepare attendees list
        event_attendees = []
        if attendees:
            event_attendees = [{'email': email} for email in attendees]
        
        event = {
            'summary': summary,
            'description': description,
            'start': {
                'dateTime': start_time.isoformat(),
                'timeZone': tz,
            },
            'end': {
                'dateTime': end_time.isoformat(),
                'timeZone': tz,
            },
            'attendees': event_attendees,
            'reminders': {
                'useDefault': False,
                'overrides': [
                    {'method': 'email', 'minutes': 24 * 60},
                    {'method': 'popup', 'minutes': 30},
                ],
            },
        }
        
        # Create the event in primary calendar
        event = calendar_service.events().insert(
            calendarId='primary',
            body=event,
            sendUpdates='all'
        ).execute()
        
        logger.info(f"Calendar event created: {event.get('htmlLink')}")
        return {
            'status': 'success',
            'event_id': event.get('id'),
            'event_link': event.get('htmlLink')
        }
        
    except Exception as e:
        logger.error(f"Error creating calendar event: {str(e)}")
        return {
            'status': 'error',
            'message': str(e)
        } 