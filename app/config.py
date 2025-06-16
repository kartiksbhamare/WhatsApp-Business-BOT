from pydantic import validator
from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional
import os
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    # App Settings
    APP_ENV: str = "development"
    PORT: int = 8000
    
    # Twilio Settings
    TWILIO_ACCOUNT_SID: str
    TWILIO_AUTH_TOKEN: str
    TWILIO_PHONE_NUMBER: str
    
    # Firebase Settings
    FIREBASE_CREDENTIALS: Optional[str] = None
    FIREBASE_KEY_PATH: str = "firebase-key.json"
    
    # Google Calendar Settings
    GOOGLE_CALENDAR_CREDENTIALS: Optional[str] = None
    GOOGLE_CALENDAR_TIMEZONE: str = "Asia/Kolkata"

    @validator('FIREBASE_CREDENTIALS')
    def validate_firebase_credentials(cls, v):
        if not v:
            logger.info("No FIREBASE_CREDENTIALS in environment, will try firebase-key.json file")
            return v
        
        try:
            creds = json.loads(v)
            required_fields = [
                "type", "project_id", "private_key_id", "private_key",
                "client_email", "client_id", "auth_uri", "token_uri"
            ]
            for field in required_fields:
                if field not in creds:
                    raise ValueError(f"Missing required field in Firebase credentials: {field}")
            logger.info("Firebase credentials validated successfully")
            return v
        except json.JSONDecodeError as e:
            logger.warning(f"Invalid Firebase credentials JSON in environment: {str(e)}")
            logger.info("Will try to load Firebase credentials from firebase-key.json file instead")
            return None  # Return None to indicate invalid env credentials, will use file instead
        except Exception as e:
            logger.warning(f"Error validating Firebase credentials: {str(e)}")
            logger.info("Will try to load Firebase credentials from firebase-key.json file instead")
            return None

    @validator('GOOGLE_CALENDAR_CREDENTIALS')
    def validate_google_calendar_credentials(cls, v):
        if not v:
            logger.warning("GOOGLE_CALENDAR_CREDENTIALS not provided")
            return v
        
        try:
            creds = json.loads(v)
            # Check for service account credentials
            if creds.get('type') == 'service_account':
                required_fields = [
                    "project_id", "private_key_id", "private_key",
                    "client_email", "client_id", "auth_uri", "token_uri"
                ]
                for field in required_fields:
                    if field not in creds:
                        raise ValueError(f"Missing required field in Google Calendar service account credentials: {field}")
                logger.info("Google Calendar service account credentials validated successfully")
                return v
            # Check for OAuth2 web credentials
            elif 'web' in creds:
                required_fields = [
                    "client_id", "project_id", "auth_uri", "token_uri",
                    "client_secret", "redirect_uris"
                ]
                for field in required_fields:
                    if field not in creds['web']:
                        raise ValueError(f"Missing required field in Google Calendar OAuth2 credentials: {field}")
                logger.info("Google Calendar OAuth2 credentials validated successfully")
                return v
            else:
                raise ValueError("Invalid Google Calendar credentials format - must be either service account or OAuth2 web credentials")
        except json.JSONDecodeError as e:
            logger.warning(f"Invalid Google Calendar credentials JSON in environment: {str(e)}")
            logger.info("Skipping invalid Google Calendar credentials from environment")
            return None
        except Exception as e:
            logger.warning(f"Error validating Google Calendar credentials: {str(e)}")
            return None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        logger.info("Environment variables loaded:")
        logger.info(f"TWILIO_ACCOUNT_SID: {'*' * len(self.TWILIO_ACCOUNT_SID) if self.TWILIO_ACCOUNT_SID else 'Not set'}")
        logger.info(f"TWILIO_AUTH_TOKEN: {'*' * len(self.TWILIO_AUTH_TOKEN) if self.TWILIO_AUTH_TOKEN else 'Not set'}")
        logger.info(f"TWILIO_PHONE_NUMBER: {self.TWILIO_PHONE_NUMBER if self.TWILIO_PHONE_NUMBER else 'Not set'}")
        logger.info(f"APP_ENV: {self.APP_ENV}")
        logger.info(f"PORT: {self.PORT}")
        logger.info(f"GOOGLE_CALENDAR_TIMEZONE: {self.GOOGLE_CALENDAR_TIMEZONE}")
        
        # Log credential status
        firebase_creds = self.get_firebase_credentials()
        logger.info(f"Firebase Credentials: {'Present' if firebase_creds else 'Not set'}")
        logger.info(f"Google Calendar Credentials: {'Present' if self.GOOGLE_CALENDAR_CREDENTIALS else 'Not set'}")
    
    def get_firebase_credentials(self) -> dict:
        """Get Firebase credentials from environment or file"""
        # First try environment variable
        if self.FIREBASE_CREDENTIALS:
            try:
                creds = json.loads(self.FIREBASE_CREDENTIALS)
                logger.info(f"Firebase Project ID: {creds.get('project_id', 'Not found')}")
                logger.info(f"Firebase Client Email: {creds.get('client_email', 'Not found')}")
                return creds
            except Exception as e:
                logger.error(f"Error parsing Firebase credentials from environment: {str(e)}")
        
        # Try to load from firebase-key.json file
        try:
            if os.path.exists(self.FIREBASE_KEY_PATH):
                with open(self.FIREBASE_KEY_PATH, 'r') as f:
                    creds = json.load(f)
                logger.info(f"Firebase credentials loaded from {self.FIREBASE_KEY_PATH}")
                logger.info(f"Firebase Project ID: {creds.get('project_id', 'Not found')}")
                logger.info(f"Firebase Client Email: {creds.get('client_email', 'Not found')}")
                return creds
            else:
                logger.warning(f"Firebase key file not found at {self.FIREBASE_KEY_PATH}")
        except Exception as e:
            logger.error(f"Error loading Firebase credentials from file: {str(e)}")
        
        return {}
    
    def get_calendar_credentials(self) -> dict:
        """Get Google Calendar credentials from environment"""
        if self.GOOGLE_CALENDAR_CREDENTIALS:
            try:
                return json.loads(self.GOOGLE_CALENDAR_CREDENTIALS)
            except Exception as e:
                logger.error(f"Error parsing Google Calendar credentials: {str(e)}")
                return {}
        return {}
    
    class Config:
        env_file = ".env"

@lru_cache()
def get_settings() -> Settings:
    logger.info("Loading settings from environment...")
    try:
        settings = Settings()
        logger.info("Settings loaded successfully!")
        return settings
    except Exception as e:
        logger.error(f"Error loading settings: {str(e)}")
        raise 