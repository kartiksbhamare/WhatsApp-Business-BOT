from app.config import get_settings
import logging

logger = logging.getLogger(__name__)

def check_twilio_config():
    """Check if Twilio configuration is properly set"""
    settings = get_settings()
    
    # Check Twilio settings
    twilio_sid = settings.TWILIO_ACCOUNT_SID
    twilio_token = settings.TWILIO_AUTH_TOKEN
    twilio_number = settings.TWILIO_PHONE_NUMBER
    
    logger.info("Twilio Configuration:")
    logger.info(f"Account SID: {'Set' if twilio_sid else 'NOT SET'}")
    logger.info(f"Auth Token: {'Set' if twilio_token else 'NOT SET'}")
    logger.info(f"Phone Number: {twilio_number if twilio_number else 'NOT SET'}")
    
    return all([twilio_sid, twilio_token, twilio_number])

def check_firebase_config():
    """Check if Firebase configuration is properly set"""
    settings = get_settings()
    
    # Check Firebase credentials
    firebase_creds = settings.get_firebase_credentials()
    
    logger.info("Firebase Configuration:")
    if firebase_creds:
        logger.info(f"Project ID: {firebase_creds.get('project_id', 'NOT FOUND')}")
        logger.info(f"Client Email: {firebase_creds.get('client_email', 'NOT FOUND')}")
    else:
        logger.info("Firebase credentials NOT SET")
    
    return bool(firebase_creds)

def run_config_check():
    """Run all configuration checks"""
    logger.info("Starting configuration check...")
    
    twilio_ok = check_twilio_config()
    firebase_ok = check_firebase_config()
    
    logger.info("\nConfiguration Check Results:")
    logger.info(f"Twilio Config: {'OK' if twilio_ok else 'MISSING'}")
    logger.info(f"Firebase Config: {'OK' if firebase_ok else 'MISSING'}")
    
    return all([twilio_ok, firebase_ok]) 