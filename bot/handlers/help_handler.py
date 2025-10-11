from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
from bot.utils.messages import get_messages

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    language = context.user_data.get('language', 'en')
    messages = get_messages(language)
    
    await update.message.reply_text(
        messages.HELP_MESSAGE,
        parse_mode='Markdown'
    )

def get_handler():
    """Return handler for this module"""
    return CommandHandler('help', help_command)