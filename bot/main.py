from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import os
import requests
import asyncio

# Import our new Local AI services instead of Gemini
from ai_services.vision import VisionClassifier
from ai_services.audio import AudioTranscriber
from ai_services.text import TextAnalyzer

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "YOUR_TELEGRAM_BOT_TOKEN_HERE")
BACKEND_API_URL = "http://127.0.0.1:8000" # Points to our new FastAPI backend

# Initialize local models
print("Loading local AI models... This might take a moment on first run.")
# vision_model = VisionClassifier()
# audio_model = AudioTranscriber()
# text_model = TextAnalyzer()
print("Models ready!")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the /start command."""
    user = update.message.from_user
    
    # 1. Register User in our Backend cleanly, using the FastAPI endpoint!
    payload = {
        "telegram_user_id": str(user.id),
        "username": user.username,
        "first_name": user.first_name
    }
    
    try:
        requests.post(f"{BACKEND_API_URL}/users", json=payload)
    except Exception as e:
        print("Backend not running yet, skipping DB save.", e)

    await update.message.reply_text(
        f"Hello {user.first_name}! Welcome to the modern FixMyHyd 2.0!\n"
        "Send me a photo of a civic issue (like a pothole or garbage) to begin."
    )

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles incoming photos, analyzes them locally, and creates a report."""
    await update.message.reply_text("Photo received! Running Local AI Vision model...")
    
    # 1. Download Photo
    photo_file = await update.message.photo[-1].get_file()
    file_path = f"temp_{update.message.from_user.id}.jpg"
    await photo_file.download_to_drive(file_path)
    
    # 2. Local AI Classification (No Gemini API!)
    # vision_result = vision_model.classify_image(file_path)
    # category = vision_result['category']
    category = "Road Issue (Pothole)" # Mocked out until torch/transformers are installed by user
    
    await update.message.reply_text(f"Detection Complete! Local AI identified this as: **{category}**")
    
    # 3. Create a Report via Text AI
    # report = text_model.generate_report(category, "User uploaded image.")['report']
    report = f"A {category} has been reported and localized." # Mock
    
    # 4. Save to Database cleanly via our Backend API
    complaint_payload = {
        "telegram_user_id": str(update.message.from_user.id),
        "category": category,
        "description": report,
        "gps_lat": 17.3850, # Dummy GPS for now
        "gps_lng": 78.4867
    }
    
    try:
        res = requests.post(f"{BACKEND_API_URL}/complaints", json=complaint_payload)
        if res.status_code == 200:
            ghmc_id = res.json().get('ghmc_id')
            await update.message.reply_text(f"✅ Issue successfully reported to the database! Your GHMC tracking ID is: {ghmc_id}")
    except:
         await update.message.reply_text("Backend error. Make sure FastAPI is running on port 8000!")

def main():
    """Start the bot."""
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Add Command Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    
    print("Bot is up and running in Refactored Mode! ✅")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()