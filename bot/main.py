import logging
from telegram.ext import Application
from config.settings import settings
from bot.handlers import start_handler, help_handler, status_handler, debug_handler
from bot.handlers import report_handler_simple as report_handler

def init_database():
    """Initialize database tables"""
    try:
        import sqlite3
        conn = sqlite3.connect('fixmyhyd.db')
        c = conn.cursor()
        
        # Create telegram_users table
        c.execute('''
            CREATE TABLE IF NOT EXISTS telegram_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_user_id TEXT UNIQUE NOT NULL,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                language_code TEXT DEFAULT 'en',
                phone_number TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create user_media table
        c.execute('''
            CREATE TABLE IF NOT EXISTS user_media (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_user_id TEXT NOT NULL,
                complaint_id INTEGER,
                media_type TEXT NOT NULL,
                upload_method TEXT,
                file_id TEXT NOT NULL,
                file_path TEXT,
                file_size INTEGER,
                file_name TEXT,
                mime_type TEXT,
                caption TEXT,
                preserves_exif BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (telegram_user_id) REFERENCES telegram_users (telegram_user_id)
            )
        ''')
        
        conn.commit()
        conn.close()
        
        if settings.DEBUG_CONSOLE:
            print("✅ Database initialized successfully")
        
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        logging.error(f"Database initialization failed: {e}")

# Configure clean logging
def setup_logging():
    """Setup clean logging configuration"""
    # Set httpx to WARNING to suppress HTTP request logs
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("telegram.ext").setLevel(logging.WARNING)
    logging.getLogger("telegram").setLevel(logging.WARNING)
    
    # Configure main logging with UTF-8 encoding
    import sys
    
    # Create file handler with UTF-8 encoding
    file_handler = logging.FileHandler('bot.log', encoding='utf-8')
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    
    # Create console handler with UTF-8 encoding
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    
    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL),
        handlers=[file_handler] + ([console_handler] if settings.LOG_LEVEL == 'DEBUG' else [])
    )

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

async def error_handler(update, context):
    """Handle errors"""
    error_msg = str(context.error)
    logger.error(f"Update {update} caused error {context.error}")
    
    # Enhanced error handling with specific messages
    if update and update.effective_message:
        try:
            # Determine error type and provide appropriate message
            if "Timed out" in error_msg:
                await update.effective_message.reply_text(
                    "⏱️ Request timed out. Please try again with a smaller image or check your connection."
                )
            elif "has no attribute" in error_msg:
                await update.effective_message.reply_text(
                    "🔧 System maintenance in progress. Please try again in a few moments."
                )
            elif "Failed to analyze" in error_msg:
                await update.effective_message.reply_text(
                    "🤖 AI analysis temporarily unavailable. You can still submit your report with a description."
                )
            elif "Connection" in error_msg or "Network" in error_msg:
                await update.effective_message.reply_text(
                    "🌐 Network issue detected. Please check your connection and try again."
                )
            else:
                await update.effective_message.reply_text(
                    "❌ Something went wrong. Please try again or use /help for assistance.\n\n"
                    "If the issue persists, contact support with error code: ERR_" + str(abs(hash(error_msg)) % 10000)
                )
        except Exception as e:
            logger.error(f"Error in error handler: {e}")
            # Fallback message if we can't send specific error
            try:
                await update.effective_message.reply_text("❌ An error occurred. Please try again.")
            except:
                pass  # Can't do much if we can't send any message

def main():
    """Start the bot"""
    # Initialize database first
    init_database()
    
    if settings.DEBUG_CONSOLE:
        print("=" * 50)
        print("🚀 Starting FixMyHyd Bot...")
        print(f"🌍 Environment: {settings.ENVIRONMENT}")
        print(f"📍 GPS Extraction: {'Enabled' if settings.ENABLE_GPS_EXTRACTION else 'Disabled'}")
        print(f"🤖 AI Analysis: {'Enabled' if settings.ENABLE_AI_CATEGORIZATION else 'Disabled'}")
        print(f"🎯 Debug Console: {'Enabled' if settings.DEBUG_CONSOLE else 'Disabled'}")
        print(f"🔗 API Base URL: {settings.API_BASE_URL}")
        print("=" * 50)
    
    logger.info("Starting FixMyHyd Bot...")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"GPS Extraction: {settings.ENABLE_GPS_EXTRACTION}")
    
    # Create application
    application = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()
    
    # Add handlers
    for handler in start_handler.get_handler():
        application.add_handler(handler)
    
    application.add_handler(help_handler.get_handler())
    application.add_handler(status_handler.get_handler())
    application.add_handler(report_handler.get_handler())
    
    # Add debug handlers
    for handler in debug_handler.get_debug_handlers():
        application.add_handler(handler)
    
    # Error handler
    application.add_error_handler(error_handler)
    
    # Start bot
    if settings.DEBUG_CONSOLE:
        print("✅ Bot is running! Press Ctrl+C to stop.")
    logger.info("Bot is running! Press Ctrl+C to stop.")
    application.run_polling(allowed_updates=['message', 'callback_query'])

if __name__ == '__main__':
    main()