from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
from bot.utils.messages import get_messages
from bot.services.api_client import APIClient
import logging

logger = logging.getLogger(__name__)
api_client = APIClient()

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /status command"""
    language = context.user_data.get('language', 'en')
    messages = get_messages(language)
    
    # Get user's complaints
    user_complaints = context.user_data.get('user_complaints', [])
    
    if not user_complaints:
        await update.message.reply_text(
            messages.NO_COMPLAINTS,
            parse_mode='Markdown'
        )
        return
    
    # Fetch complaint details from API
    await update.message.reply_text("🔍 Fetching your complaints...")
    
    try:
        complaints = api_client.get_user_complaints(user_complaints)
        
        if complaints:
            response = "📊 *Your Complaints*\n\n"
            
            for complaint in complaints[:5]:  # Show last 5
                ghmc_id = complaint.get('ghmc_id', 'N/A')
                status = complaint.get('status', 'Unknown')
                category = complaint.get('category', 'Unknown')
                created_at = complaint.get('created_at', 'Unknown')
                
                status_emoji = {
                    'Submitted': '🟡',
                    'In Progress': '🔵',
                    'Resolved': '🟢',
                    'Rejected': '🔴'
                }.get(status, '⚪')
                
                response += (
                    f"{status_emoji} *{ghmc_id}*\n"
                    f"   Category: {category}\n"
                    f"   Status: {status}\n"
                    f"   Date: {created_at}\n\n"
                )
            
            response += "\n_Showing last 5 complaints_"
            
            await update.message.reply_text(response, parse_mode='Markdown')
        else:
            await update.message.reply_text(
                "❌ Could not fetch complaint details. Please try again later."
            )
    
    except Exception as e:
        logger.error(f"Error fetching complaints: {e}")
        await update.message.reply_text(
            "❌ An error occurred while fetching your complaints."
        )

def get_handler():
    """Return handler for this module"""
    return CommandHandler('status', status_command)