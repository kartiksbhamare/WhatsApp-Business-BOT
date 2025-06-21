import os
import logging
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    """Application settings"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True
    )
    
    # Venom Bot Settings
    VENOM_SERVICE_URL: str = "http://localhost:3000"
    
    # Firebase Settings
    FIREBASE_PROJECT_ID: str
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
        self._setup_logging()
        self._validate_settings()
    
    def _setup_logging(self):
        """Setup logging configuration"""
        logging.basicConfig(
            level=getattr(logging, self.LOG_LEVEL.upper()),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    def _validate_settings(self):
        """Validate required settings and log configuration"""
        logger.info("Configuration loaded:")
        logger.info(f"DEBUG: {self.DEBUG}")
        logger.info(f"LOG_LEVEL: {self.LOG_LEVEL}")
        
        # Firebase validation
        logger.info(f"FIREBASE_PROJECT_ID: {self.FIREBASE_PROJECT_ID if self.FIREBASE_PROJECT_ID else 'Not set'}")
        logger.info(f"FIREBASE_CREDENTIALS_PATH: {self.FIREBASE_CREDENTIALS_PATH}")
        
        if not os.path.exists(self.FIREBASE_CREDENTIALS_PATH):
            logger.warning(f"Firebase credentials file not found: {self.FIREBASE_CREDENTIALS_PATH}")
        
        # Venom Bot validation
        logger.info(f"VENOM_SERVICE_URL: {self.VENOM_SERVICE_URL}")
        
        # Google Calendar validation (optional)
        if self.GOOGLE_CALENDAR_CREDENTIALS_PATH:
            logger.info(f"GOOGLE_CALENDAR_CREDENTIALS_PATH: {self.GOOGLE_CALENDAR_CREDENTIALS_PATH}")
            if not os.path.exists(self.GOOGLE_CALENDAR_CREDENTIALS_PATH):
                logger.warning(f"Google Calendar credentials file not found: {self.GOOGLE_CALENDAR_CREDENTIALS_PATH}")
        else:
            logger.info("Google Calendar integration disabled (no credentials path)")
        
        if self.GOOGLE_CALENDAR_ID:
            logger.info(f"GOOGLE_CALENDAR_ID: {self.GOOGLE_CALENDAR_ID}")
        else:
            logger.info("Google Calendar ID not set")

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