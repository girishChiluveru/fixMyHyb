from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackQueryHandler, ContextTypes
from bot.utils.messages import get_messages
from bot.utils.debug_logger import DebugLogger
from bot.services.api_client import api_client
import logging

logger = logging.getLogger(__name__)
debug = DebugLogger(__name__)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    user = update.effective_user
    
    # Debug logging for user interaction
    debug.user_joined(user.username, str(user.id))
    
    # Store user data in context (temporary storage)
    context.user_data['telegram_id'] = user.id
    context.user_data['username'] = user.username
    context.user_data['first_name'] = user.first_name
    
    # Save user data to database immediately
    user_data = {
        'telegram_user_id': str(user.id),
        'username': user.username,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'language_code': user.language_code
    }
    
    try:
        save_result = api_client.save_user_data(user_data)
        if save_result and save_result.get('status') == 'success':
            debug.user_saved_to_db(user.username)
            debug.console_log(f"[START HANDLER] ✅ User {user.username} saved to database")
        else:
            debug.console_log(f"[START HANDLER] ⚠️ Failed to save user data: {save_result}")
    except Exception as e:
        debug.console_log(f"[START HANDLER] ❌ Error saving user data: {e}")
        logger.error(f"Failed to save user data for {user.id}: {e}")
    
    # Check if user language is set
    language = context.user_data.get('language', 'en')
    messages = get_messages(language)
    
    # Determine if new user (simple check - can be enhanced with database)
    is_new_user = 'last_interaction' not in context.user_data
    
    if is_new_user:
        message = messages.WELCOME_NEW_USER.format(first_name=user.first_name)
        
        # Language selection keyboard
        keyboard = [
            [
                InlineKeyboardButton("English 🇬🇧", callback_data='lang_en'),
                InlineKeyboardButton("తెలుగు 🇮🇳", callback_data='lang_te')
            ],
            [InlineKeyboardButton("हिंदी 🇮🇳", callback_data='lang_hi')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            message,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    else:
        message = messages.WELCOME_BACK.format(first_name=user.first_name)
        await update.message.reply_text(message, parse_mode='Markdown')
    
    # Update last interaction
    context.user_data['last_interaction'] = 'start'

async def language_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle language selection callback"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    
    # Extract language code
    language = query.data.split('_')[1]  # lang_en -> en
    context.user_data['language'] = language
    
    # Update user data in database with selected language
    user_data = {
        'telegram_user_id': str(user.id),
        'username': user.username,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'language_code': language
    }
    
    try:
        save_result = api_client.save_user_data(user_data)
        if save_result and save_result.get('status') == 'success':
            debug.console_log(f"[START HANDLER] ✅ Updated language for user {user.username} to {language}")
        else:
            debug.console_log(f"[START HANDLER] ⚠️ Failed to update user language: {save_result}")
    except Exception as e:
        debug.console_log(f"[START HANDLER] ❌ Error updating user language: {e}")
        logger.error(f"Failed to update language for user {user.id}: {e}")
    
    # Confirmation message
    lang_names = {'en': 'English', 'te': 'తెలుగు', 'hi': 'हिंदी'}
    await query.edit_message_text(
        f"✅ Language set to {lang_names[language]}!\n\n"
        f"Type /report to report your first civic issue! 📸"
    )

def get_handler():
    """Return handlers for this module"""
    return [
        CommandHandler('start', start_command),
        CallbackQueryHandler(language_callback, pattern='^lang_')
    ]