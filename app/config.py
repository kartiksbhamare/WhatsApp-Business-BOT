import os
import logging
from typing import Optional, Dict
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    """Application settings"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra='allow'  # Allow extra fields for backward compatibility
    )
    
    # WhatsApp Web Service Settings - with backward compatibility
    WHATSAPP_SERVICE_URL: str = "http://localhost:3000"  # WhatsApp service runs on port 3000
    VENOM_SERVICE_URL: Optional[str] = None  # For backward compatibility
    
    # Multi-Salon WhatsApp Service URLs
    SALON_A_WHATSAPP_URL: str = "http://localhost:3005"
    SALON_B_WHATSAPP_URL: str = "http://localhost:3006"
    SALON_C_WHATSAPP_URL: str = "http://localhost:3007"
    
    # Multi-Salon Phone Numbers
    SALON_A_PHONE: str = "+1234567890"
    SALON_B_PHONE: str = "+0987654321"
    SALON_C_PHONE: str = "+1122334455"
    
    # Firebase Settings - made optional with defaults for Railway deployment
    FIREBASE_PROJECT_ID: str = "appointment-booking-4c50f"  # Default project ID
    FIREBASE_CREDENTIALS_PATH: str = "firebase-key.json"
    
    # Google Calendar Settings (optional)
    GOOGLE_CALENDAR_CREDENTIALS_PATH: Optional[str] = "client_secret.json"
    GOOGLE_CALENDAR_TOKEN_PATH: Optional[str] = "token.json"
    GOOGLE_CALENDAR_ID: Optional[str] = None
    
    # App Settings
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._handle_backward_compatibility()
        self._setup_logging()
        self._validate_settings()
    
    def _handle_backward_compatibility(self):
        """Handle backward compatibility for renamed environment variables"""
        # If VENOM_SERVICE_URL is set but WHATSAPP_SERVICE_URL is default, use the old value
        if self.VENOM_SERVICE_URL and self.WHATSAPP_SERVICE_URL == "http://localhost:3000":
            self.WHATSAPP_SERVICE_URL = self.VENOM_SERVICE_URL
            logger.info("Using VENOM_SERVICE_URL for backward compatibility. Please update to WHATSAPP_SERVICE_URL")
    
    def _setup_logging(self):
        """Setup logging configuration"""
        logging.basicConfig(
            level=getattr(logging, self.LOG_LEVEL.upper()),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    @property
    def salon_phone_mapping(self) -> Dict[str, str]:
        """Get phone to salon ID mapping"""
        return {
            # Remove the + from phone numbers for matching
            "1234567890": "salon_a",        # Downtown Beauty Salon
            "0987654321": "salon_b",        # Uptown Hair Studio  
            "1122334455": "salon_c",        # Luxury Spa & Salon
            "919307748525": "salon_a",      # Your current phone number -> salon_a
            # Add default mapping for backward compatibility
            "default": "salon_a"
        }
    
    @property
    def salon_whatsapp_mapping(self) -> Dict[str, str]:
        """Get salon ID to WhatsApp service URL mapping - all use main service for Railway deployment"""
        return {
            "salon_a": self.WHATSAPP_SERVICE_URL,
            "salon_b": self.WHATSAPP_SERVICE_URL,
            "salon_c": self.WHATSAPP_SERVICE_URL,
            # Add default salon for backward compatibility
            "default": self.WHATSAPP_SERVICE_URL
        }
    
    def get_salon_from_phone(self, to_phone: str) -> str:
        """Get salon ID from receiving phone number"""
        cleaned_phone = to_phone.replace("+", "").replace("@c.us", "")
        return self.salon_phone_mapping.get(cleaned_phone, "salon_a")  # Default to 'salon_a' which exists in database
    
    def get_whatsapp_url_for_salon(self, salon_id: str) -> str:
        """Get WhatsApp service URL for a specific salon"""
        return self.salon_whatsapp_mapping.get(salon_id, self.WHATSAPP_SERVICE_URL)
    
    def _validate_settings(self):
        """Validate required settings and log configuration"""
        logger.info("✅ Smart WhatsApp Booking Bot Configuration loaded:")
        logger.info(f"🔧 DEBUG: {self.DEBUG}")
        logger.info(f"📊 LOG_LEVEL: {self.LOG_LEVEL}")
        
        # Firebase validation
        logger.info(f"🔥 FIREBASE_PROJECT_ID: {self.FIREBASE_PROJECT_ID}")
        logger.info(f"📄 FIREBASE_CREDENTIALS_PATH: {self.FIREBASE_CREDENTIALS_PATH}")
        
        if not os.path.exists(self.FIREBASE_CREDENTIALS_PATH):
            logger.warning(f"⚠️ Firebase credentials file not found: {self.FIREBASE_CREDENTIALS_PATH}")
            logger.info("💡 This is normal during Railway deployment - credentials will be created from environment variable")
        else:
            logger.info("✅ Firebase credentials file found")
        
        # WhatsApp Web Service validation
        logger.info(f"📱 WHATSAPP_SERVICE_URL: {self.WHATSAPP_SERVICE_URL}")
        
        # Google Calendar validation (optional)
        if self.GOOGLE_CALENDAR_CREDENTIALS_PATH:
            logger.info(f"📅 GOOGLE_CALENDAR_CREDENTIALS_PATH: {self.GOOGLE_CALENDAR_CREDENTIALS_PATH}")
            if not os.path.exists(self.GOOGLE_CALENDAR_CREDENTIALS_PATH):
                logger.warning(f"⚠️ Google Calendar credentials file not found: {self.GOOGLE_CALENDAR_CREDENTIALS_PATH}")
        else:
            logger.info("📅 Google Calendar integration disabled (no credentials path)")
        
        if self.GOOGLE_CALENDAR_ID:
            logger.info(f"🗓️ GOOGLE_CALENDAR_ID: {self.GOOGLE_CALENDAR_ID}")
        else:
            logger.info("🗓️ Google Calendar ID not set")

# Global settings instance
_settings: Optional[Settings] = None

def get_settings() -> Settings:
    """Get application settings (singleton)"""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings

def reload_settings():
    """Reload settings (useful for testing)"""
    global _settings
    _settings = None
    return get_settings() 