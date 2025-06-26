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
    
    # Service URL Configuration - Environment-based, no hardcoded localhost
    BACKEND_URL: str = "http://localhost:8000"  # Default for local development
    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000
    
    WHATSAPP_SERVICE_URL: str = "http://localhost:3000"  # Default for local development  
    WHATSAPP_HOST: str = "0.0.0.0"
    WHATSAPP_PORT: int = 3000
    
    # Salon Configuration
    SALON_NAME: str = "Beauty Salon"
    
    # Firebase Settings
    FIREBASE_PROJECT_ID: str = "appointment-booking-4c50f"
    FIREBASE_CREDENTIALS_PATH: str = "firebase-key.json"
    FIREBASE_CREDENTIALS_BASE64: Optional[str] = None  # For Railway deployment
    
    # Google Calendar Settings (optional)
    GOOGLE_CALENDAR_CREDENTIALS_PATH: Optional[str] = "client_secret.json"
    GOOGLE_CALENDAR_TOKEN_PATH: Optional[str] = "token.json"
    GOOGLE_CALENDAR_ID: Optional[str] = None
    
    # App Settings
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    
    # Environment Detection
    RAILWAY_ENVIRONMENT: Optional[str] = None
    DOCKER_ENV: Optional[str] = None
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._detect_environment()
        self._handle_backward_compatibility()
        self._setup_logging()
        self._validate_settings()
    
    def _detect_environment(self):
        """Detect deployment environment and adjust URLs accordingly"""
        # Auto-detect Railway environment
        if os.getenv("RAILWAY_ENVIRONMENT") or os.getenv("PORT"):
            logger.info("🚂 Railway environment detected")
            # In Railway, use internal service communication or public URLs
            railway_url = os.getenv("RAILWAY_STATIC_URL") or os.getenv("RAILWAY_PUBLIC_DOMAIN")
            if railway_url:
                # Use Railway public URLs if available
                protocol = "https" if not railway_url.startswith("localhost") else "http"
                self.BACKEND_URL = f"{protocol}://{railway_url}"
                self.WHATSAPP_SERVICE_URL = f"{protocol}://{railway_url}"
                logger.info(f"🔗 Using Railway URLs: {self.BACKEND_URL}")
        
        # Auto-detect Docker environment
        elif os.getenv("DOCKER_ENV") or os.path.exists("/.dockerenv"):
            logger.info("🐳 Docker environment detected")
            # In Docker, use service names for internal communication
            self.BACKEND_URL = "http://backend:8000"
            self.WHATSAPP_SERVICE_URL = "http://whatsapp:3000"
        
        # Local development - use defaults
        else:
            logger.info("💻 Local development environment detected")
    
    def _handle_backward_compatibility(self):
        """Handle backward compatibility for renamed environment variables"""
        # Handle legacy VENOM_SERVICE_URL
        legacy_venom_url = os.getenv("VENOM_SERVICE_URL")
        if legacy_venom_url and not os.getenv("WHATSAPP_SERVICE_URL"):
            self.WHATSAPP_SERVICE_URL = legacy_venom_url
            logger.warning("⚠️ Using deprecated VENOM_SERVICE_URL. Please update to WHATSAPP_SERVICE_URL")
    
    def _setup_logging(self):
        """Setup logging configuration"""
        logging.basicConfig(
            level=getattr(logging, self.LOG_LEVEL.upper()),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    def _validate_settings(self):
        """Validate required settings and log configuration"""
        logger.info("✅ Smart WhatsApp Booking Bot Configuration loaded:")
        logger.info(f"🔧 DEBUG: {self.DEBUG}")
        logger.info(f"📊 LOG_LEVEL: {self.LOG_LEVEL}")
        
        # Service URLs
        logger.info(f"🔗 BACKEND_URL: {self.BACKEND_URL}")
        logger.info(f"📱 WHATSAPP_SERVICE_URL: {self.WHATSAPP_SERVICE_URL}")
        logger.info(f"🏢 SALON_NAME: {self.SALON_NAME}")
        
        # Firebase validation
        logger.info(f"🔥 FIREBASE_PROJECT_ID: {self.FIREBASE_PROJECT_ID}")
        logger.info(f"📄 FIREBASE_CREDENTIALS_PATH: {self.FIREBASE_CREDENTIALS_PATH}")
        
        if self.FIREBASE_CREDENTIALS_BASE64:
            logger.info("🔑 Using base64 Firebase credentials (Railway deployment)")
        elif not os.path.exists(self.FIREBASE_CREDENTIALS_PATH):
            logger.warning(f"⚠️ Firebase credentials file not found: {self.FIREBASE_CREDENTIALS_PATH}")
        else:
            logger.info("✅ Firebase credentials file found")
        
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