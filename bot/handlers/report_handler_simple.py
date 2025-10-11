"""
Simplified and modular report handler - no keyboard buttons required
"""
import os
import logging
from datetime import datetime
from telegram import Update, ReplyKeyboardRemove
from telegram.ext import (
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters
)
from bot.utils.gps_extractor import GPSExtractor
from bot.utils.messages import get_messages
from bot.utils.debug_logger import DebugLogger
from bot.utils.session_manager import session_manager
from bot.utils.fallback_analyzer import fallback_analyzer
from bot.services.api_client import APIClient
from config.settings import settings

# Import modular components
from .report_handler_modules import (
    ImageProcessor, LocationHandler, SubmissionHandler, 
    UserInputHandler, ResponseFormatter
)

logger = logging.getLogger(__name__)
debug = DebugLogger(__name__)

# Conversation states
WAITING_FOR_PHOTO, WAITING_FOR_DETAILS, WAITING_FOR_LOCATION, WAITING_FOR_VOICE, WAITING_FOR_CONFIRMATION = range(5)

# Initialize API client
api_client = APIClient()

async def start_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start the complaint reporting process"""
    user_id = str(update.effective_user.id)
    
    # Check if user has an active session
    active_session_id = session_manager.get_user_active_session(user_id)
    
    if active_session_id:
        session_summary = session_manager.get_session_summary(active_session_id)
        
        await update.message.reply_text(
            f"📋 **You have an active session:**\n\n{session_summary}\n\n"
            "**Choose what to do:**\n"
            "• Type **continue** to keep working on it\n"
            "• Type **new** to start a fresh report\n"
            "• Type **cancel** to cancel the old session",
            parse_mode='Markdown'
        )
        
        context.user_data['pending_session_choice'] = True
        context.user_data['active_session_id'] = active_session_id
        return WAITING_FOR_PHOTO
    
    # Create new session
    session_id = session_manager.create_session(user_id)
    context.user_data['session_id'] = session_id
    context.user_data['report_data'] = {}
    
    debug.info(f"[SESSION] Started new report session {session_id} for user {user_id}")
    
    await update.message.reply_text(
        "📸 *Start Your Complaint Report*\n\n"
        f"*Session ID: {session_id}*\n\n"
        "Please send a clear photo of the civic issue you want to report.\n\n"
        "💡 *Tip:* Send as a file/document to preserve location data.",
        parse_mode='Markdown'
    )
    
    return WAITING_FOR_PHOTO

async def handle_image_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle image uploads - simplified version"""
    # Handle session choice first
    if context.user_data.get('pending_session_choice') and update.message.text:
        return await handle_session_choice(update, context)
    
    # Get session ID
    session_id = context.user_data.get('session_id')
    if not session_id:
        await update.message.reply_text("❌ No active session. Use /report to start a new report.")
        return ConversationHandler.END
    
    # Determine upload type and file info
    is_document, file_info = get_file_info(update)
    if not file_info:
        await update.message.reply_text("❌ Please send an image file.")
        return WAITING_FOR_PHOTO
    
    # Save user data
    await save_user_data(update)
    
    # Show processing message
    upload_type = "document" if is_document else "photo"
    processing_msg = await update.message.reply_text(f"📥 Processing {upload_type}...")

    try:
        # Download and store image
        file_path, caption = await ImageProcessor.download_and_store_image(
            update, context, file_info, is_document
        )
        
        # Process GPS
        user_id = str(update.effective_user.id)
        gps_result = await LocationHandler.extract_gps_from_image(
            file_path, user_id, session_id, context
        )
        
        # Update processing message with GPS result
        await update_gps_status(processing_msg, gps_result, upload_type)
        
        # Process AI analysis
        filename = getattr(file_info, 'file_name', f"image.jpg")
        await update.message.reply_text("🤖 Analyzing image with AI...")
        
        analysis_result = await ImageProcessor.process_ai_analysis(
            file_path, filename, session_id, context
        )
        
        # Show AI analysis result
        if analysis_result['success']:
            await update.message.reply_text(
                ResponseFormatter.format_ai_analysis_message(analysis_result),
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                "⚠️ *AI Analysis Failed*\n\n"
                "Please add a detailed description of the issue.",
                parse_mode='Markdown'
            )
        
        # Handle caption if provided
        if caption and caption.strip():
            await handle_image_caption(update, context, caption, session_id)
        
        # Ask for additional details
        return await ask_for_details(update, context)
        
    except Exception as e:
        debug.error(f"Error processing image upload: {e}")
        await processing_msg.edit_text("❌ Error processing image. Please try again.")
        return WAITING_FOR_PHOTO

async def handle_voice_or_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle voice notes and text descriptions - simplified"""
    session_id = context.user_data.get('session_id')
    if not session_id:
        await update.message.reply_text("❌ No active session. Use /report to start a new report.")
        return ConversationHandler.END
    
    # Handle voice note
    if update.message.voice:
        return await process_voice_note(update, context, session_id)
    
    # Handle text
    if update.message.text:
        text = update.message.text.strip().lower()
        
        # Handle session management commands
        if text in ['submit', 'done', 'finish', 'ready', 'send']:
            session_status = session_manager.is_session_ready(session_id)
            if session_status['ready']:
                return await show_confirmation(update, context)
            else:
                await update.message.reply_text(
                    f"⚠️ **Cannot submit yet!**\n\n"
                    f"Missing: {', '.join(session_status['missing'])}\n\n"
                    "Please add more information first.",
                    parse_mode='Markdown'
                )
                return await ask_for_details(update, context)
        
        elif text in ['add', 'more', 'continue', 'edit']:
            await update.message.reply_text(
                "✍️ **Add More Details**\n\n"
                "Type your additional description below:",
                parse_mode='Markdown'
            )
            return WAITING_FOR_VOICE
        
        elif text in ['status', 'check', 'info']:
            session_summary = session_manager.get_session_summary(session_id)
            session_status = session_manager.is_session_ready(session_id)
            
            await update.message.reply_text(
                f"📋 **Session Status**\n\n{session_summary}\n\n"
                f"Status: {'✅ Ready to submit' if session_status['ready'] else '⚠️ Missing: ' + ', '.join(session_status['missing'])}",
                parse_mode='Markdown'
            )
            return await ask_for_details(update, context)
        
        elif text in ['cancel', 'stop', 'quit', 'abort']:
            return await cancel_report(update, context)
        
        elif text in ['help', 'commands']:
            await update.message.reply_text(
                "📋 **Available Commands:**\n\n"
                "• **submit** - Submit your report\n"
                "• **add** - Add more description\n"
                "• **status** - Check session status\n"
                "• **cancel** - Cancel report\n"
                "• **help** - Show this help\n\n"
                "Or just type your description directly!",
                parse_mode='Markdown'
            )
            return WAITING_FOR_VOICE
        
        # Regular description (not a command)
        else:
            original_text = update.message.text.strip()
            cleaned_text = UserInputHandler.clean_user_description(original_text)
            session_manager.add_description(session_id, cleaned_text)
            
            await update.message.reply_text(
                f"✅ **Description Added**\n\n_{cleaned_text}_\n\n"
                "Type **submit** when ready, or **add** for more details.",
                parse_mode='Markdown'
            )
            
            return await ask_for_details(update, context)
    
    await update.message.reply_text(
        "Please send:\n• Text description\n• Voice note\n• Type **help** for commands"
    )
    return WAITING_FOR_VOICE

async def show_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show confirmation - no keyboard buttons"""
    report_data = context.user_data['report_data']
    
    # Validate requirements
    has_image = 'image_analysis' in report_data
    has_description = 'caption' in report_data or session_manager.get_session(context.user_data['session_id']).get('descriptions')
    
    if not has_image:
        await update.message.reply_text("❌ Image is required. Please send an image first.")
        return WAITING_FOR_PHOTO
    
    if not has_description:
        await update.message.reply_text("⚠️ Please add a description before submitting.")
        return WAITING_FOR_VOICE
    
    # Show confirmation
    confirmation_message = ResponseFormatter.format_confirmation_message(report_data)
    
    await update.message.reply_text(
        confirmation_message + "\n\n"
        "**Final confirmation:**\n"
        "• Type **yes** or **confirm** to submit\n"
        "• Type **no** or **cancel** to cancel\n"
        "• Type **back** to add more details",
        parse_mode='Markdown'
    )
    
    return WAITING_FOR_CONFIRMATION

async def handle_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle final submission - simplified"""
    response = update.message.text.strip().lower()
    
    # Check for cancellation
    if response in ['no', 'cancel', 'stop', 'abort', 'quit']:
        await update.message.reply_text(
            "❌ **Complaint cancelled**\n\nUse /report to start again."
        )
        cleanup_temp_files(context)
        context.user_data.clear()
        return ConversationHandler.END
    
    # Check for going back
    if response in ['back', 'edit', 'modify', 'change']:
        await update.message.reply_text(
            "⬅️ **Going back to add details**\n\nYou can add more descriptions or voice notes."
        )
        return await ask_for_details(update, context)
    
    # Check for confirmation
    if response in ['yes', 'confirm', 'submit', 'send', 'ok', 'proceed']:
        return await submit_complaint(update, context)
    
    # Unrecognized response
    await update.message.reply_text(
        "❓ **Please respond with:**\n"
        "• **yes** or **confirm** to submit\n"
        "• **no** or **cancel** to cancel\n"
        "• **back** to add more details"
    )
    return WAITING_FOR_CONFIRMATION

# Helper functions
def get_file_info(update: Update):
    """Get file info and determine if it's a document"""
    if update.message.document and update.message.document.mime_type and update.message.document.mime_type.startswith('image/'):
        return True, update.message.document
    elif update.message.photo:
        return False, update.message.photo[-1]
    return False, None

async def save_user_data(update: Update):
    """Save user data to database"""
    user = update.effective_user
    debug.user_joined(user.username, str(user.id))
    
    user_data = {
        'telegram_user_id': str(user.id),
        'username': user.username,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'language_code': user.language_code
    }
    api_client.save_user_data(user_data)
    debug.user_saved_to_db(user.username)

async def handle_session_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle session choice when user has active session"""
    text = update.message.text.lower().strip()
    user_id = str(update.effective_user.id)
    
    if text in ["continue", "cont", "resume"]:
        session_id = context.user_data['active_session_id']
        context.user_data['session_id'] = session_id
        context.user_data['pending_session_choice'] = False
        
        session_status = session_manager.is_session_ready(session_id)
        
        if session_status['ready']:
            await update.message.reply_text(
                f"📋 **Continuing session {session_id}**\n\n"
                "✅ Your session is ready to submit!\n\n"
                "Type **submit** to send to GHMC or **add** for more details.",
                parse_mode='Markdown'
            )
            return await ask_for_details(update, context)
        else:
            await update.message.reply_text(
                f"📋 **Continuing session {session_id}**\n\n"
                "Send an image or add more details to continue.",
                parse_mode='Markdown'
            )
            return WAITING_FOR_PHOTO
        
    elif text in ["new", "fresh", "start"]:
        # Cancel old session and create new one
        session_manager.cancel_session(context.user_data['active_session_id'])
        session_id = session_manager.create_session(user_id)
        context.user_data['session_id'] = session_id
        context.user_data['pending_session_choice'] = False
        context.user_data['report_data'] = {}
        
        await update.message.reply_text(
            f"🆕 **Started new session {session_id}**\n\n"
            "Please send an image of the civic issue.",
            parse_mode='Markdown'
        )
        return WAITING_FOR_PHOTO
    
    elif text in ["cancel", "stop", "abort"]:
        # Cancel the active session
        session_manager.cancel_session(context.user_data['active_session_id'])
        context.user_data['pending_session_choice'] = False
        
        await update.message.reply_text(
            "❌ **Active session cancelled**\n\n"
            "Use /report to start a new complaint report.",
            parse_mode='Markdown'
        )
        return ConversationHandler.END
    
    await update.message.reply_text(
        "Please type one of:\n• **continue** - Resume active session\n• **new** - Start fresh\n• **cancel** - Cancel active session"
    )
    return WAITING_FOR_PHOTO

async def update_gps_status(processing_msg, gps_result: dict, upload_type: str):
    """Update processing message with GPS status"""
    if gps_result['success']:
        message = ResponseFormatter.format_gps_success_message(gps_result, upload_type)
        await processing_msg.edit_text(message, parse_mode='Markdown', disable_web_page_preview=True)
    else:
        if gps_result.get('no_cache'):
            await processing_msg.edit_text(
                f"✅ {upload_type.title()} processed!\n⚠️ No GPS data found\n\n"
                "💡 You can add location details in your description."
            )
        else:
            await processing_msg.edit_text(f"✅ {upload_type.title()} processed successfully!")

async def handle_image_caption(update: Update, context: ContextTypes.DEFAULT_TYPE, caption: str, session_id: str):
    """Handle image caption as description"""
    session_manager.add_description(session_id, caption.strip())
    context.user_data['report_data']['description'] = caption.strip()
    debug.info(f"[SESSION] Added caption as description: {caption[:50]}...")
    
    await update.message.reply_text(
        f"📝 *Caption saved as description:*\n_{caption}_",
        parse_mode='Markdown'
    )

async def ask_for_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ask for additional details - no keyboard"""
    session_id = context.user_data.get('session_id')
    session_status = session_manager.is_session_ready(session_id)
    
    status_text = "📝 *Add Details*\n\n"
    
    if session_status['ready']:
        status_text += "✅ *Ready to submit!*\n\n"
        status_text += "Type one of these commands:\n"
        status_text += "• **submit** - Submit your report to GHMC\n"
        status_text += "• **add** - Add more description\n"
        status_text += "• **voice** - Send a voice note\n"
        status_text += "• **cancel** - Cancel this report\n"
    else:
        status_text += f"⚠️ *Missing:* {', '.join(session_status['missing'])}\n\n"
        status_text += "Please provide more information:\n"
        status_text += "• Type a description of the issue\n"
        status_text += "• Send a voice note\n"
        status_text += "• Type **add** to add more details\n"
        status_text += "• Type **cancel** to cancel\n"
    
    status_text += "\n_At least one description is required._"
    
    await update.message.reply_text(
        status_text,
        parse_mode='Markdown'
    )
    return WAITING_FOR_VOICE

async def process_voice_note(update: Update, context: ContextTypes.DEFAULT_TYPE, session_id: str):
    """Process voice note"""
    voice = update.message.voice
    processing_msg = await update.message.reply_text("🎤 Transcribing voice note...")
    
    try:
        # Download voice
        file = await context.bot.get_file(voice.file_id)
        voice_path = os.path.join(settings.TEMP_DIR, f"{voice.file_id}.ogg")
        await file.download_to_drive(voice_path)
        
        # Store voice data
        voice_data = {
            'type': 'voice',
            'file_id': voice.file_id,
            'file_path': voice_path,
            'file_size': voice.file_size,
            'duration': voice.duration,
            'timestamp': datetime.now().isoformat()
        }
        
        session_manager.add_voice(session_id, voice_data)
        
        # Transcribe
        transcription_result = api_client.transcribe_voice(voice_path)
        
        if transcription_result and transcription_result.get('status') == 'success':
            transcription = transcription_result.get('transcription', '')
            session_manager.add_description(session_id, f"[Voice Note] {transcription}")
            
            await processing_msg.edit_text(
                f"✅ *Voice Transcribed*\n\n_{transcription}_\n\n"
                "Type 'submit' when ready, or add more details.",
                parse_mode='Markdown'
            )
        else:
            await processing_msg.edit_text("⚠️ Voice transcription failed, but voice saved.")
        
        # Clean up
        if os.path.exists(voice_path):
            os.remove(voice_path)
        
        return WAITING_FOR_VOICE
            
    except Exception as e:
        debug.error(f"Error processing voice note: {e}")
        await processing_msg.edit_text("❌ Error processing voice note.")
        return WAITING_FOR_VOICE

async def submit_complaint(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Submit complaint to GHMC"""
    await update.message.reply_text("📤 Submitting to GHMC portal... Please wait.")
    
    try:
        report_data = context.user_data['report_data']
        session_id = context.user_data.get('session_id')
        
        # Prepare payload
        payload = await SubmissionHandler.prepare_submission_payload(report_data)
        
        # Create draft complaint
        draft_complaint = SubmissionHandler.create_draft_complaint(
            report_data, payload['text_analysis']
        )
        
        # Save draft complaint
        if session_id:
            session_manager.save_draft_complaint(session_id, draft_complaint)
        
        # Submit to backend
        debug.console_log("[REPORT HANDLER] 📤 Submitting report to backend...")
        result = api_client.generate_and_submit_report(payload)
        
        if result and result.get('status') == 'success':
            ghmc_id = result.get('ghmc_id')
            complaint_id = result.get('complaint_id')
            
            # Print detailed complaint summary to console
            if session_id:
                session_manager.print_complaint_summary(session_id, draft_complaint)
            
            debug.console_log(f"[REPORT HANDLER] ✅ Report submitted successfully! GHMC ID: {ghmc_id}")
            
            success_message = (
                f"✅ *Complaint Submitted Successfully!*\n\n"
                f"*GHMC ID:* `{ghmc_id}`\n"
                f"*Internal ID:* #{complaint_id}\n"
                f"*Timestamp:* {datetime.now().strftime('%d %b %Y, %I:%M %p')}\n\n"
                "You'll receive updates on this complaint.\n"
                "Use /status to check progress anytime."
            )
            
            await update.message.reply_text(success_message, parse_mode='Markdown')
        else:
            debug.error("Failed to submit complaint to backend")
            await update.message.reply_text(
                "❌ Failed to submit complaint. Please try again later."
            )

    except Exception as e:
        debug.error(f"Error submitting complaint: {e}")
        await update.message.reply_text(
            "❌ An error occurred during submission. Please try again."
        )
    
    finally:
        cleanup_temp_files(context)
        context.user_data['report_data'] = {}
    
    return ConversationHandler.END

def cleanup_temp_files(context: ContextTypes.DEFAULT_TYPE):
    """Clean up temporary files"""
    try:
        report_data = context.user_data.get('report_data', {})
        image_path = report_data.get('image_path')
        if image_path and os.path.exists(image_path):
            os.remove(image_path)
            logger.info(f"Cleaned up: {image_path}")
    except Exception as e:
        logger.error(f"Error cleaning up files: {e}")

async def cancel_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel the reporting process"""
    cleanup_temp_files(context)
    await update.message.reply_text("❌ Report cancelled.")
    context.user_data.clear()
    return ConversationHandler.END

def get_handler():
    """Return the conversation handler"""
    return ConversationHandler(
        entry_points=[
            CommandHandler('report', start_report),
            MessageHandler(filters.PHOTO & ~filters.COMMAND, handle_image_upload),
            MessageHandler(filters.Document.IMAGE & ~filters.COMMAND, handle_image_upload)
        ],
        states={
            WAITING_FOR_PHOTO: [
                MessageHandler(filters.PHOTO, handle_image_upload),
                MessageHandler(filters.Document.IMAGE, handle_image_upload),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_image_upload),
            ],
            WAITING_FOR_VOICE: [
                MessageHandler(filters.VOICE, handle_voice_or_text),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_voice_or_text),
            ],
            WAITING_FOR_CONFIRMATION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_confirmation),
            ],
        },
        fallbacks=[
            CommandHandler('cancel', cancel_report)
        ],
    )