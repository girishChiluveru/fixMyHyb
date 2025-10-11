"""
Debug Handler for testing connectivity and system status
"""
from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
from bot.utils.debug_logger import DebugLogger
from bot.services.api_client import APIClient
from config.settings import settings
import requests

debug = DebugLogger(__name__)


async def debug_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Debug command to check system status"""
    
    status_text = "🔍 *System Status Check*\n\n"
    
    # Check API client
    api_client = APIClient()
    
    # Test backend connectivity
    status_text += "**Backend Connectivity:**\n"
    try:
        health_check = api_client.check_backend_health()
        if health_check:
            status_text += f"✅ Backend: Online ({settings.API_BASE_URL})\n"
        else:
            status_text += f"❌ Backend: Offline ({settings.API_BASE_URL})\n"
    except Exception as e:
        status_text += f"❌ Backend: Error - {e}\n"
    
    # Test specific endpoints
    status_text += "\n**API Endpoints:**\n"
    endpoints = [
        ("/health", "Health check"),
        ("/api/analyze-image", "Image analysis"),
        ("/api/transcribe-voice", "Voice transcription"),
        ("/api/users", "User management")
    ]
    
    for endpoint, description in endpoints:
        try:
            url = f"{settings.API_BASE_URL}{endpoint}"
            response = requests.get(url if endpoint == "/health" else url.replace("/api/", "/"), timeout=5)
            if response.status_code < 500:
                status_text += f"✅ {description}: Available\n"
            else:
                status_text += f"⚠️ {description}: Error {response.status_code}\n"
        except requests.exceptions.ConnectionError:
            status_text += f"❌ {description}: Connection failed\n"
        except Exception as e:
            status_text += f"❌ {description}: {str(e)[:50]}\n"
    
    # Check settings
    status_text += "\n**Configuration:**\n"
    status_text += f"🌍 Environment: {settings.ENVIRONMENT}\n"
    status_text += f"📍 GPS Extraction: {'✅' if settings.ENABLE_GPS_EXTRACTION else '❌'}\n"
    status_text += f"🤖 AI Analysis: {'✅' if settings.ENABLE_AI_CATEGORIZATION else '❌'}\n"
    status_text += f"🎯 Debug Console: {'✅' if settings.DEBUG_CONSOLE else '❌'}\n"
    
    await update.message.reply_text(status_text, parse_mode='Markdown')


async def debug_test_ai(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Test AI analysis with a sample request"""
    
    await update.message.reply_text("🧪 Testing AI connectivity...\n\nPlease send an image to test AI analysis.")
    
    # Set flag to test next image
    context.user_data['debug_test_mode'] = True


def get_debug_handlers():
    """Get debug command handlers"""
    return [
        CommandHandler('debug_status', debug_status),
        CommandHandler('debug_ai', debug_test_ai)
    ]