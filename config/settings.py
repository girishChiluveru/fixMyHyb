# import os
# from dotenv import load_dotenv

# load_dotenv()

# class Settings:
#     # Telegram
#     TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    
#     # Environment
#     ENVIRONMENT = os.getenv('ENVIRONMENT', 'development')
#     LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    
#     # Features
#     ENABLE_GPS_EXTRACTION = os.getenv('ENABLE_GPS_EXTRACTION', 'true').lower() == 'true'
#     ENABLE_AI_CATEGORIZATION = os.getenv('ENABLE_AI_CATEGORIZATION', 'false').lower() == 'true'
#     ENABLE_GHMC_SUBMISSION = os.getenv('ENABLE_GHMC_SUBMISSION', 'false').lower() == 'true'
    
#     # Paths
#     TEMP_DIR = 'temp'

# settings = Settings()
import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    # Telegram
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    
    # Google API
    GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
    
    # Flask API Backend
    API_BASE_URL = os.getenv('API_BASE_URL', 'http://localhost:5001')
    
    # Environment
    ENVIRONMENT = os.getenv('ENVIRONMENT', 'development')
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    
    # Debug Settings
    DEBUG_CONSOLE = os.getenv('DEBUG_CONSOLE', 'true').lower() == 'true'
    
    # Features
    ENABLE_GPS_EXTRACTION = os.getenv('ENABLE_GPS_EXTRACTION', 'true').lower() == 'true'
    ENABLE_AI_CATEGORIZATION = os.getenv('ENABLE_AI_CATEGORIZATION', 'true').lower() == 'true'  # Changed to true
    ENABLE_GHMC_SUBMISSION = os.getenv('ENABLE_GHMC_SUBMISSION', 'true').lower() == 'true'  # Changed to true
    
    # Paths
    TEMP_DIR = 'temp'

settings = Settings()