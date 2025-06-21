import logging
from app.config import get_settings
from app.services.whatsapp import check_whatsapp_service_health

logger = logging.getLogger(__name__)

def check_whatsapp_config():
    """Check if WhatsApp Web service is available"""
    settings = get_settings()
    
    logger.info("WhatsApp Web Service Configuration:")
    logger.info(f"Service URL: {settings.WHATSAPP_SERVICE_URL}")
    
    # Check if WhatsApp Web service is running
    is_ready = check_whatsapp_service_health()
    logger.info(f"Service Status: {'Ready' if is_ready else 'Not Ready/Unreachable'}")
    
    return is_ready

def check_firebase_config():
    """Check if Firebase configuration is properly set"""
    settings = get_settings()
    
    logger.info("Firebase Configuration:")
    logger.info(f"Project ID: {'Set' if settings.FIREBASE_PROJECT_ID else 'NOT SET'}")
    logger.info(f"Credentials Path: {settings.FIREBASE_CREDENTIALS_PATH}")
    
    # Check if Firebase credentials file exists
    import os
    creds_exist = os.path.exists(settings.FIREBASE_CREDENTIALS_PATH)
    logger.info(f"Credentials File Exists: {'Yes' if creds_exist else 'No'}")
    
    return all([settings.FIREBASE_PROJECT_ID, creds_exist])

def run_config_check():
    """Run comprehensive configuration check"""
    logger.info("=" * 50)
    logger.info("CONFIGURATION CHECK")
    logger.info("=" * 50)
    
    whatsapp_ok = check_whatsapp_config()
    firebase_ok = check_firebase_config()
    
    logger.info("=" * 50)
    logger.info("SUMMARY")
    logger.info("=" * 50)
    logger.info(f"WhatsApp Web Service: {'OK' if whatsapp_ok else 'ISSUE'}")
    logger.info(f"Firebase Config: {'OK' if firebase_ok else 'MISSING'}")
    
    overall_status = firebase_ok  # WhatsApp service might not be ready during startup
    logger.info(f"Overall Status: {'READY' if overall_status else 'NEEDS ATTENTION'}")
    
    if not whatsapp_ok:
        logger.warning("⚠️ WhatsApp Web service is not ready. Make sure to start it with 'npm start' or 'node whatsapp-service.js'")
    
    return overall_status 