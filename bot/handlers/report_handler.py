import os
import logging
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton
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

logger = logging.getLogger(__name__)
debug = DebugLogger(__name__)

# Conversation states
WAITING_FOR_PHOTO, WAITING_FOR_DETAILS, WAITING_FOR_LOCATION, WAITING_FOR_VOICE, WAITING_FOR_CONFIRMATION = range(5)

# Initialize API client
api_client = APIClient()

async def start_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start the complaint reporting process"""
    language = context.user_data.get('language', 'en')
    messages = get_messages(language)
    
    # Get or create user session
    user_id = str(update.effective_user.id)
    
    # Check if user has an active session
    active_session_id = session_manager.get_user_active_session(user_id)
    
    if active_session_id:
        session = session_manager.get_session(active_session_id)
        session_summary = session_manager.get_session_summary(active_session_id)
        
        keyboard = [
            ["📸 Continue Current Session"],
            ["🆕 Start New Session"],
            ["❌ Cancel Current Session"]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
        
        await update.message.reply_text(
            f"You have an active session:\n\n{session_summary}\n\n"
            "What would you like to do?",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        
        context.user_data['pending_session_choice'] = True
        context.user_data['active_session_id'] = active_session_id
        return WAITING_FOR_PHOTO
    
    # Create new session
    session_id = session_manager.create_session(user_id)
    context.user_data['session_id'] = session_id
    context.user_data['report_data'] = {}  # Keep for compatibility
    
    debug.info(f"[SESSION] Started new report session {session_id} for user {user_id}")
    
    await update.message.reply_text(
        "📸 *Start Your Complaint Report*\n\n"
        f"*Session ID: {session_id}*\n\n"
        "*Step 1: Send a photo/image of the issue*\n\n"
        "📌 *Choose your upload method:*\n"
        "• 📷 *Send as Photo* - Quick but location may be removed\n"
        "• 📎 *Send as File/Document* - Preserves GPS location data\n"
        "• 📍 *Send location separately* if needed\n\n"
        "💡 *For best results*: Use 📎 *Attach File* → *Gallery* → Select image\n\n"
        "Please send a clear image of the civic issue you want to report.",
        parse_mode='Markdown'
    )
    
    return WAITING_FOR_PHOTO

async def handle_image_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle both photo and document image uploads - REQUIRED"""
    language = context.user_data.get('language', 'en')
    messages = get_messages(language)
    
    # Handle session choice first
    if context.user_data.get('pending_session_choice'):
        text = update.message.text
        user_id = str(update.effective_user.id)
        
        if "Continue Current Session" in text:
            session_id = context.user_data['active_session_id']
            context.user_data['session_id'] = session_id
            context.user_data['pending_session_choice'] = False
            
            await update.message.reply_text(
                f"📋 *Continuing Session {session_id}*\n\n"
                "You can add more images, descriptions, or voice notes to your report.\n"
                "Send an image to continue.",
                parse_mode='Markdown'
            )
            return WAITING_FOR_PHOTO
            
        elif "Start New Session" in text:
            # Cancel old session and create new one
            session_manager.cancel_session(context.user_data['active_session_id'])
            session_id = session_manager.create_session(user_id)
            context.user_data['session_id'] = session_id
            context.user_data['pending_session_choice'] = False
            
            await update.message.reply_text(
                f"🆕 *Started New Session {session_id}*\n\n"
                "Please send an image of the civic issue you want to report.",
                parse_mode='Markdown'
            )
            return WAITING_FOR_PHOTO
            
        elif "Cancel Current Session" in text:
            session_manager.cancel_session(context.user_data['active_session_id'])
            context.user_data['pending_session_choice'] = False
            
            await update.message.reply_text(
                "❌ *Session Cancelled*\n\n"
                "Use /report to start a new complaint report.",
                parse_mode='Markdown'
            )
            return ConversationHandler.END
        else:
            await update.message.reply_text("Please choose one of the options above.")
            return WAITING_FOR_PHOTO
    
    # Get session ID
    session_id = context.user_data.get('session_id')
    if not session_id:
        await update.message.reply_text("❌ No active session. Use /report to start a new report.")
        return ConversationHandler.END
    
    # Determine if it's a photo or document
    is_document = False
    file_info = None
    caption = update.message.caption or ""
    
    if update.message.document and update.message.document.mime_type and update.message.document.mime_type.startswith('image/'):
        # Image sent as document (preserves EXIF)
        is_document = True
        file_info = update.message.document
        logger.info("[UPLOAD_DEBUG] Image received as DOCUMENT - EXIF data preserved")
    elif update.message.photo:
        # Image sent as photo (compressed, EXIF stripped)
        is_document = False
        file_info = update.message.photo[-1]  # Get highest resolution
        logger.info("[UPLOAD_DEBUG] Image received as PHOTO - EXIF data likely stripped")
    else:
        await update.message.reply_text("❌ Please send an image file (photo or document).")
        return WAITING_FOR_PHOTO
    
    # NEW: Save user data
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
    
    # Send processing message
    upload_type = "document" if is_document else "photo"
    processing_msg = await update.message.reply_text(
        f"📥 Processing {upload_type}...\n"
        f"{'🔒 EXIF data preserved' if is_document else '⚠️ EXIF may be stripped'}"
    )

    try:
        # Download file
        file = await context.bot.get_file(file_info.file_id)
        file_extension = ".jpg"
        if is_document and hasattr(file_info, 'file_name') and file_info.file_name:
            file_extension = os.path.splitext(file_info.file_name)[1] or ".jpg"
        
        file_path = os.path.join(settings.TEMP_DIR, f"{file_info.file_id}{file_extension}")
        await file.download_to_drive(file_path)
        
        # Debug logging for file upload
        filename = getattr(file_info, 'file_name', f"image{file_extension}")
        debug.file_uploaded(filename, upload_type)
        
        logger.info(f"File downloaded: {file_path}")
        logger.info(f"File ID: {file_info.file_id}")
        logger.info(f"File size: {file_info.file_size}")
        logger.info(f"Upload type: {'Document' if is_document else 'Photo'}")
        logger.info(f"Caption: {caption}")
        
        # Store image data in session
        image_data = {
            'type': 'image',
            'upload_method': upload_type,
            'file_id': file_info.file_id,
            'file_path': file_path,
            'file_size': file_info.file_size,
            'file_name': getattr(file_info, 'file_name', None),
            'mime_type': getattr(file_info, 'mime_type', 'image/jpeg'),
            'caption': caption,
            'preserves_exif': is_document,
            'timestamp': datetime.now().isoformat()
        }
        
        session_manager.add_image(session_id, image_data)
        
        # Also store in report_data for compatibility
        if 'report_data' not in context.user_data:
            context.user_data['report_data'] = {}
        
        context.user_data['report_data']['image_path'] = file_path
        context.user_data['report_data']['caption'] = caption
        context.user_data['report_data']['telegram_user_id'] = str(user.id)
        context.user_data['report_data']['upload_type'] = upload_type
        context.user_data['report_data']['session_id'] = session_id
        
        # Step 1: Extract GPS from image
        gps_result = None
        user_id = str(update.effective_user.id)
        
        if settings.ENABLE_GPS_EXTRACTION:
            gps_extractor = GPSExtractor()
            gps_result = gps_extractor.extract_for_telegram(file_path)
            
            logger.info(f"GPS extraction result: {gps_result}")
            
            if gps_result['success']:
                gps_data = {
                    'latitude': gps_result['latitude'],
                    'longitude': gps_result['longitude'],
                    'source': 'exif',
                    'maps_url': gps_result['maps_url']
                }
                
                # Cache GPS for user to avoid asking again
                session_manager.cache_user_gps(user_id, gps_data)
                
                session_manager.set_gps_data(session_id, gps_data)
                context.user_data['report_data']['gps_lat'] = gps_result['latitude']
                context.user_data['report_data']['gps_lng'] = gps_result['longitude']
                context.user_data['report_data']['has_gps'] = True
                
                debug.gps_extracted(gps_result['latitude'], gps_result['longitude'], filename)
                
                await processing_msg.edit_text(
                    f"✅ *{upload_type.title()} processed successfully!*\n\n"
                    f"📍 *GPS Location Found & Cached:*\n"
                    f"Lat: {gps_result['latitude']:.6f}\n"
                    f"Lon: {gps_result['longitude']:.6f}\n\n"
                    f"[📍 View on Map]({gps_result['maps_url']})\n\n"
                    f"💡 *Location saved for future reports*",
                    parse_mode='Markdown',
                    disable_web_page_preview=True
                )
            else:
                context.user_data['report_data']['has_gps'] = False
                debug.gps_extraction_failed(gps_result.get('error', 'Unknown'), filename)
                
                # Check for cached GPS first
                cached_gps = session_manager.get_cached_gps(user_id)
                if cached_gps:
                    # Use cached GPS coordinates
                    context.user_data['report_data']['gps_lat'] = cached_gps['latitude']
                    context.user_data['report_data']['gps_lng'] = cached_gps['longitude']
                    context.user_data['report_data']['has_gps'] = True
                    
                    await processing_msg.edit_text(
                        f"✅ *{upload_type.title()} processed successfully!*\n\n"
                        f"📍 *Using Previously Saved Location*\n"
                        f"Lat: {cached_gps['latitude']:.6f}\n"
                        f"Lon: {cached_gps['longitude']:.6f}\n\n"
                        f"[📍 View on Map]({cached_gps['maps_url']})\n\n"
                        f"💡 *Location from previous session*",
                        parse_mode='Markdown',
                        disable_web_page_preview=True
                    )
                else:
                    # Ask for location sharing if no GPS and no cache
                    await processing_msg.edit_text(
                        f"✅ *{upload_type.title()} processed successfully!*\n\n"
                        f"⚠️ *No GPS data found*\n"
                        f"Reason: {gps_result.get('error', 'Unknown')}\n\n"
                        f"{'💡 Try sending as Document next time' if not is_document else '📱 Camera may not have GPS enabled'}"
                    )
                    
                    # Ask for location sharing
                    from telegram import KeyboardButton, ReplyKeyboardMarkup
                    location_keyboard = [
                        [KeyboardButton("📍 Share My Current Location", request_location=True)],
                        ["⏭️ Continue Without Location"]
                    ]
                    location_markup = ReplyKeyboardMarkup(location_keyboard, resize_keyboard=True, one_time_keyboard=True)
                    
                    await update.message.reply_text(
                        "🗺️ *Location Needed for Accurate Reporting*\n\n"
                        "GHMC needs to know the exact location to respond effectively.\n\n"
                        "Please share your current location:",
                        parse_mode='Markdown',
                        reply_markup=location_markup
                    )
                    
                    # Set state to wait for location
                    context.user_data['waiting_for_location'] = True
                context.user_data['waiting_for_location'] = True
        
        # Step 2: Analyze image with AI
        await update.message.reply_text("🤖 Analyzing image with AI...")
        debug.console_log(f"[REPORT HANDLER] 🤖 Starting AI analysis for: {filename}")
        debug.ai_analysis_started(filename)
        
        image_analysis = api_client.analyze_image(file_path)
        
        if image_analysis and image_analysis.get('status') == 'success':
            analysis_data = image_analysis.get('analysis', {})
            debug.console_log(f"[REPORT HANDLER] ✅ AI analysis successful: {analysis_data.get('category', 'Unknown')}")
            
            # Store AI analysis in session
            session_manager.set_ai_analysis(session_id, analysis_data)
            context.user_data['report_data']['image_analysis'] = analysis_data
            
            category = analysis_data.get('category', 'Unknown')
            summary = analysis_data.get('summary', 'Analysis completed')
            source = image_analysis.get('source', 'api')
            
            debug.ai_analysis_completed(category, filename)
            
            response_text = (
                f"🤖 *AI Analysis Complete*\n\n"
                f"*🏷️ Category:* {category}\n"
                f"*📝 Summary:* {summary}\n"
            )
            
            if source == 'fallback':
                response_text += f"*⚠️ Source:* Offline analysis (backend unavailable)\n"
            
            if gps_result and gps_result['success']:
                response_text += f"*📍 Location:* Available\n"
            
            response_text += "\n"
            
            await update.message.reply_text(
                response_text,
                parse_mode='Markdown'
            )
        elif image_analysis and image_analysis.get('fallback'):
            # Try fallback analysis
            debug.info(f"[FALLBACK] Attempting offline image analysis")
            await update.message.reply_text("🔄 Backend unavailable, trying offline analysis...")
            
            fallback_result = fallback_analyzer.analyze_image_basic(file_path, caption)
            
            if fallback_result and fallback_result.get('status') == 'success':
                analysis_data = fallback_result.get('analysis', {})
                
                # Store fallback analysis in session
                session_manager.set_ai_analysis(session_id, analysis_data)
                context.user_data['report_data']['image_analysis'] = analysis_data
                
                category = analysis_data.get('category', 'Unknown')
                summary = analysis_data.get('summary', 'Basic analysis completed')
                
                debug.ai_analysis_completed(f"{category} (fallback)", filename)
                
                response_text = (
                    f"🔄 *Offline Analysis Complete*\n\n"
                    f"*🏷️ Category:* {category}\n"
                    f"*📝 Summary:* {summary}\n"
                    f"*⚠️ Note:* Basic analysis used (backend unavailable)\n\n"
                )
                
                if gps_result and gps_result['success']:
                    response_text += f"*📍 Location:* Available\n\n"
                
                await update.message.reply_text(
                    response_text,
                    parse_mode='Markdown'
                )
            else:
                debug.error("Both AI analysis and fallback analysis failed")
                await update.message.reply_text(
                    "⚠️ *Analysis Failed*\n\n"
                    "Both online and offline analysis failed. "
                    "Please add a detailed description to help categorize your report.",
                    parse_mode='Markdown'
                )
        else:
            debug.error("AI analysis failed - no fallback available")
            await update.message.reply_text(
                "⚠️ *AI Analysis Failed*\n\n"
                "Could not analyze the image automatically. "
                "Please add a detailed description of the issue.",
                parse_mode='Markdown'
            )
        
        # Check if we have a caption to use as description
        if caption and caption.strip():
            session_manager.add_description(session_id, caption.strip())
            context.user_data['report_data']['description'] = caption.strip()
            debug.info(f"[SESSION] Added caption as description: {caption[:50]}...")
            
            # Check if session is ready for submission
            session_status = session_manager.is_session_ready(session_id)
            
            if session_status['ready']:
                await update.message.reply_text(
                    f"📝 *Using image caption as description:*\n_{caption}_\n\n"
                    "✅ Session has all required data. Proceeding to final review...",
                    parse_mode='Markdown'
                )
                return await show_confirmation(update, context)
            else:
                await update.message.reply_text(
                    f"📝 *Added caption as description:*\n_{caption}_\n\n"
                    "You can add more images, voice notes, or descriptions before submitting.",
                    parse_mode='Markdown'
                )
        
        # Show session status and options
        session_status = session_manager.is_session_ready(session_id)
        return await show_session_options(update, context, session_status)
        
    except Exception as e:
        debug.error(f"Error processing image upload: {e}")
        await processing_msg.edit_text("❌ Error processing image. Please try again.")
        return WAITING_FOR_PHOTO

async def show_session_options(update: Update, context: ContextTypes.DEFAULT_TYPE, session_status: dict):
    """Show current session status and available options"""
    session_id = context.user_data.get('session_id')
    session_summary = session_manager.get_session_summary(session_id)
    
    keyboard = []
    
    if session_status['ready']:
        keyboard.append(["✅ Submit Report"])
    
    keyboard.extend([
        ["📸 Add More Images", "🎤 Add Voice Note"],
        ["✍️ Add Description", "📍 Add Location"],
        ["📋 View Session", "❌ Cancel Session"]
    ])
    
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    
    status_text = f"{session_summary}\n\n"
    
    if session_status['ready']:
        status_text += "✅ *Ready to submit!*\n\n"
    else:
        status_text += f"⚠️ *Missing:* {', '.join(session_status['missing'])}\n\n"
    
    status_text += "What would you like to do next?"
    
    await update.message.reply_text(
        status_text,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )
    
    return WAITING_FOR_VOICE

async def ask_for_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ask for voice note or text description"""
    # Ask for voice note or text description (at least one is required)
    keyboard = [
        ["🎤 Send Voice Note"],
        ["✍️ Type Description"],
        ["⏭️ Skip to Submit"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    
    await update.message.reply_text(
        "📝 *Add More Details*\n\n"
        "Please provide additional information by:\n"
        "• Recording a voice note 🎤\n"
        "• Typing a description ✍️\n\n"
        "_Note: At least image + (voice OR text) is required_",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )
    
    return WAITING_FOR_DETAILS

async def handle_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle location sharing"""
    location = update.message.location
    user_id = str(update.effective_user.id)
    
    if location:
        # Create GPS data object
        gps_data = {
            'latitude': location.latitude,
            'longitude': location.longitude,
            'source': 'user_shared',
            'maps_url': f"https://www.google.com/maps?q={location.latitude},{location.longitude}"
        }
        
        # Store GPS coordinates from shared location
        context.user_data['report_data']['gps_lat'] = location.latitude
        context.user_data['report_data']['gps_lng'] = location.longitude
        context.user_data['report_data']['has_gps'] = True
        context.user_data['waiting_for_location'] = False
        
        # Cache GPS for future use
        session_manager.cache_user_gps(user_id, gps_data)
        
        logger.info(f"[GPS_DEBUG] Location shared by user: {location.latitude}, {location.longitude}")
        
        await update.message.reply_text(
            f"✅ *Location Received & Cached!*\n\n"
            f"📍 Lat: {location.latitude:.6f}, Lon: {location.longitude:.6f}\n"
            f"[View on Map](https://www.google.com/maps?q={location.latitude},{location.longitude})\n\n"
            f"💡 *Location saved for future reports*",
            parse_mode='Markdown',
            disable_web_page_preview=True
        )
        
        return await ask_for_details(update, context)
    else:
        await update.message.reply_text("❌ No location data received. Please try again.")
        return WAITING_FOR_LOCATION

async def handle_document_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle image sent as document (preserves EXIF data)"""
    document = update.message.document
    
    # Check if it's an image document
    if not document.mime_type or not document.mime_type.startswith('image/'):
        await update.message.reply_text("❌ Please send an image file.")
        return WAITING_FOR_PHOTO
    
    # Process as photo but with preserved EXIF data
    logger.info("[EXIF_DEBUG] Processing image document with preserved EXIF data")
    
    # Temporarily set photo object for existing handler
    class DocumentAsPhoto:
        def __init__(self, document):
            self.file_id = document.file_id
            self.file_size = document.file_size
    
    # Store original message
    original_photo = update.message.photo
    original_document = update.message.document
    
    # Temporarily replace photo with document info
    update.message.photo = [DocumentAsPhoto(document)]
    update.message.document = document
    
    # Call the existing image handler
    result = await handle_image_upload(update, context)
    
    # Restore original message
    update.message.photo = original_photo
    update.message.document = original_document
    
    return result

async def handle_voice_or_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle voice note, text description, or session options"""
    session_id = context.user_data.get('session_id')
    if not session_id:
        await update.message.reply_text("❌ No active session. Use /report to start a new report.")
        return ConversationHandler.END
    
    # Handle text-based options first
    if update.message.text:
        text = update.message.text
        
        if "Add More Images" in text:
            await update.message.reply_text(
                "📸 *Add Another Image*\n\n"
                "Send another image of the issue to add to your report.",
                parse_mode='Markdown'
            )
            return WAITING_FOR_PHOTO
            
        elif "Add Voice Note" in text:
            await update.message.reply_text(
                "🎤 *Record Voice Note*\n\n"
                "Record a voice message describing the issue in detail.",
                parse_mode='Markdown'
            )
            return WAITING_FOR_VOICE
            
        elif "Add Description" in text:
            await update.message.reply_text(
                "✍️ *Type Description*\n\n"
                "Please type a detailed description of the civic issue:",
                parse_mode='Markdown'
            )
            return WAITING_FOR_VOICE
            
        elif "Add Location" in text:
            location_keyboard = [
                [KeyboardButton("📍 Share My Current Location", request_location=True)],
                ["⏭️ Skip Location"]
            ]
            location_markup = ReplyKeyboardMarkup(location_keyboard, resize_keyboard=True, one_time_keyboard=True)
            
            await update.message.reply_text(
                "📍 *Share Location*\n\n"
                "Please share your current location or the location of the issue:",
                parse_mode='Markdown',
                reply_markup=location_markup
            )
            return WAITING_FOR_LOCATION
            
        elif "View Session" in text:
            session_summary = session_manager.get_session_summary(session_id)
            session_status = session_manager.is_session_ready(session_id)
            
            await update.message.reply_text(
                f"{session_summary}\n\n"
                f"Status: {'✅ Ready to submit' if session_status['ready'] else '⚠️ Missing: ' + ', '.join(session_status['missing'])}",
                parse_mode='Markdown'
            )
            return await show_session_options(update, context, session_status)
            
        elif "Cancel Session" in text:
            session_manager.cancel_session(session_id)
            await update.message.reply_text(
                "❌ *Session Cancelled*\n\n"
                "Use /report to start a new complaint report.",
                parse_mode='Markdown'
            )
            return ConversationHandler.END
            
        elif "Submit Report" in text:
            session_status = session_manager.is_session_ready(session_id)
            if session_status['ready']:
                return await show_confirmation(update, context)
            else:
                await update.message.reply_text(
                    f"⚠️ Cannot submit yet. Missing: {', '.join(session_status['missing'])}\n\n"
                    "Please add the required information first.",
                    parse_mode='Markdown'
                )
                return await show_session_options(update, context, session_status)
        
        # Handle regular text description
        elif not any(keyword in text for keyword in ["Skip", "Continue", "Cancel"]):
            # This is a regular description
            session_manager.add_description(session_id, text)
            debug.info(f"[SESSION] Added description: {text[:50]}...")
            
            await update.message.reply_text(
                f"✅ *Description Added*\n\n"
                f"_{text}_\n\n"
                "Description saved to your session.",
                parse_mode='Markdown'
            )
            
            session_status = session_manager.is_session_ready(session_id)
            return await show_session_options(update, context, session_status)
    
    # Handle voice note
    if update.message.voice:
        voice = update.message.voice
        processing_msg = await update.message.reply_text("🎤 Transcribing voice note...")
        
        try:
            # Download voice
            file = await context.bot.get_file(voice.file_id)
            voice_path = os.path.join(settings.TEMP_DIR, f"{voice.file_id}.ogg")
            await file.download_to_drive(voice_path)
            
            voice_filename = f"voice_{voice.file_id}.ogg"
            debug.voice_transcription_started(voice_filename)
            
            # Store voice data in session
            voice_data = {
                'type': 'voice',
                'file_id': voice.file_id,
                'file_path': voice_path,
                'file_size': voice.file_size,
                'duration': voice.duration,
                'timestamp': datetime.now().isoformat()
            }
            
            session_manager.add_voice(session_id, voice_data)
            
            logger.info(f"Voice downloaded: {voice_path}")
            logger.info(f"Voice file_id: {voice.file_id}")
            logger.info(f"Voice file_size: {voice.file_size}")
            logger.info(f"Voice duration: {voice.duration}")
            
            # Transcribe with API
            transcription_result = api_client.transcribe_voice(voice_path)
            
            if transcription_result and transcription_result.get('status') == 'success':
                transcription = transcription_result.get('transcription', '')
                
                # Add transcription as description
                session_manager.add_description(session_id, f"[Voice Note] {transcription}")
                
                debug.voice_transcription_completed(voice_filename)
                
                await processing_msg.edit_text(
                    f"✅ *Voice Transcribed*\n\n"
                    f"_{transcription}_\n\n"
                    "Voice note saved to your session.",
                    parse_mode='Markdown'
                )
            else:
                debug.error(f"Voice transcription failed for {voice_filename}")
                await processing_msg.edit_text("⚠️ Voice transcription failed, but voice note saved.")
                
            # Clean up
            if os.path.exists(voice_path):
                os.remove(voice_path)
            
            session_status = session_manager.is_session_ready(session_id)
            return await show_session_options(update, context, session_status)
                
        except Exception as e:
            debug.error(f"Error processing voice note: {e}")
            await processing_msg.edit_text("❌ Error processing voice note.")
            return WAITING_FOR_VOICE
    
    # If we get here, it's probably an unhandled case
    await update.message.reply_text("Please use one of the provided options.")
    session_status = session_manager.is_session_ready(session_id)
    return await show_session_options(update, context, session_status)

async def show_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show complaint summary and ask for confirmation"""
    report_data = context.user_data['report_data']
    
    # Validate: Must have image + (voice OR text)
    has_image = 'image_analysis' in report_data
    has_voice = 'voice_transcription' in report_data
    has_text = 'text_analysis' in report_data or 'user_description' in report_data or 'caption' in report_data
    
    if not has_image:
        await update.message.reply_text("❌ Image is mandatory. Please send an image first.")
        return WAITING_FOR_PHOTO
    
    if not has_voice and not has_text:
        await update.message.reply_text(
            "⚠️ Please provide either a voice note or text description to continue.",
            reply_markup=ReplyKeyboardRemove()
        )
        return WAITING_FOR_DETAILS
    
    # Build summary
    image_data = report_data.get('image_analysis', {})
    text_data = report_data.get('text_analysis', {})
    
    category = text_data.get('category') or image_data.get('category', 'Other')
    priority = text_data.get('priority', 'Medium')
    summary = text_data.get('summary') or image_data.get('summary', 'Issue detected')
    
    location_text = "GPS Available" if report_data.get('has_gps') else "No GPS"
    
    summary_message = (
        f"📋 *Complaint Summary*\n\n"
        f"*Category:* {category}\n"
        f"*Priority:* {priority}\n"
        f"*Description:* {summary}\n"
        f"*Location:* {location_text}\n\n"
        f"*Confirm Submission?*\n"
        f"This will be sent to GHMC official portal."
    )
    
    keyboard = [["✅ YES - Submit to GHMC", "❌ NO - Cancel"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    
    await update.message.reply_text(
        summary_message,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )
    
    return WAITING_FOR_CONFIRMATION

async def handle_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle final submission"""
    response = update.message.text
    
    # Handle explicit button responses
    if 'Cancel' in response or '❌' in response:
        await update.message.reply_text(
            "❌ Complaint cancelled. Use /report to start again.",
            reply_markup=ReplyKeyboardRemove()
        )
        # Clean up files
        cleanup_temp_files(context)
        context.user_data.clear()
        return ConversationHandler.END
    
    # Handle confirmation responses (buttons or text)
    confirm_keywords = ['confirm', 'submit', '✅', 'yes', 'y', 'ok', 'proceed']
    if any(keyword in response.lower() for keyword in confirm_keywords) or 'Confirm & Submit' in response:
        # Submit to backend
        await update.message.reply_text(
            "📤 Submitting to GHMC portal... Please wait.",
            reply_markup=ReplyKeyboardRemove()
        )
        
        try:
            report_data = context.user_data['report_data']
            
            # Prepare payload for API
            # If we have a caption but no text_analysis, create one from the caption
            text_analysis = report_data.get('text_analysis')
            if not text_analysis and report_data.get('caption'):
                debug.console_log("[REPORT HANDLER] 📝 Creating text analysis from caption...")
                try:
                    caption_analysis = api_client.analyze_text(report_data.get('caption'))
                    if caption_analysis and caption_analysis.get('status') == 'success':
                        text_analysis = caption_analysis.get('analysis', {})
                        debug.console_log(f"[REPORT HANDLER] ✅ Caption analysis: {text_analysis.get('category', 'Unknown')}")
                    else:
                        # Create basic text analysis from caption
                        text_analysis = {
                            'category': 'Other',
                            'summary': report_data.get('caption', 'User provided description'),
                            'source': 'caption_fallback'
                        }
                        debug.console_log("[REPORT HANDLER] 📝 Using fallback analysis for caption")
                except Exception as e:
                    debug.console_log(f"[REPORT HANDLER] ❌ Caption analysis failed: {e}")
                    text_analysis = {
                        'category': 'Other',
                        'summary': report_data.get('caption', 'User provided description'),
                        'source': 'caption_fallback'
                    }
            
            payload = {
                'image_analysis': report_data.get('image_analysis'),
                'voice_transcription': report_data.get('voice_transcription'),
                'text_analysis': text_analysis,
                'location_text': report_data.get('caption', ''),
                'gps_lat': report_data.get('gps_lat'),
                'gps_lng': report_data.get('gps_lng'),
                'telegram_user_id': report_data.get('telegram_user_id'),
                'media_files': report_data.get('media_files', [])
            }
            
            # Submit to backend
            debug.console_log("[REPORT HANDLER] 📤 Submitting report to backend...")
            
            # Create draft complaint for GHMC
            session_id = context.user_data.get('session_id')
            draft_complaint = {
                'issue_type': text_analysis.get('category', 'Other') if text_analysis else 'Other',
                'priority': 'Medium',  # Can be enhanced with AI priority detection
                'subject': f"Civic Issue Report - {text_analysis.get('category', 'General')}",
                'description': text_analysis.get('summary', report_data.get('caption', 'No description provided')),
                'location': report_data.get('caption', 'Location not specified'),
                'latitude': report_data.get('gps_lat'),
                'longitude': report_data.get('gps_lng'),
                'maps_url': f"https://www.google.com/maps?q={report_data.get('gps_lat')},{report_data.get('gps_lng')}" if report_data.get('gps_lat') else None,
                'telegram_user_id': report_data.get('telegram_user_id'),
                'media_files': report_data.get('media_files', []),
                'ai_analysis': report_data.get('image_analysis'),
                'text_analysis': text_analysis
            }
            
            # Save draft complaint
            if session_id:
                session_manager.save_draft_complaint(session_id, draft_complaint)
            
            result = api_client.generate_and_submit_report(payload)
            
            if result and result.get('status') == 'success':
                ghmc_id = result.get('ghmc_id')
                complaint_id = result.get('complaint_id')
                category = report_data.get('image_analysis', {}).get('category', 'Unknown')
                
                # Print detailed complaint summary to console
                if session_id:
                    session_manager.print_complaint_summary(session_id, draft_complaint)
                
                debug.console_log(f"[REPORT HANDLER] ✅ Report submitted successfully! GHMC ID: {ghmc_id}")
                debug.report_submitted(ghmc_id or complaint_id, category)
                
                # Store GHMC ID for user
                if 'user_complaints' not in context.user_data:
                    context.user_data['user_complaints'] = []
                context.user_data['user_complaints'].append(ghmc_id)
                
                success_message = (
                    f"✅ *Complaint Submitted Successfully!*\n\n"
                    f"*GHMC ID:* `{ghmc_id}`\n"
                    f"*Internal ID:* #{complaint_id}\n"
                    f"*Timestamp:* {datetime.now().strftime('%d %b %Y, %I:%M %p')}\n\n"
                    f"You'll receive updates on this complaint.\n"
                    f"Use /status to check progress anytime."
                )
                
                await update.message.reply_text(success_message, parse_mode='Markdown')
            else:
                debug.error("Failed to submit complaint to backend")
                await update.message.reply_text(
                    "❌ Failed to submit complaint. Please try again later or contact support."
                )
    
        except Exception as e:
            debug.error(f"Error submitting complaint: {e}")
            await update.message.reply_text(
                "❌ An error occurred during submission. Please try again."
            )
        
        finally:
            # Clean up
            cleanup_temp_files(context)
            context.user_data['report_data'] = {}
        
        return ConversationHandler.END
    
    else:
        # Handle unrecognized response - ask again with clearer options
        keyboard = [
            ["✅ YES - Submit to GHMC"],
            ["❌ NO - Cancel Report"]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
        
        await update.message.reply_text(
            "❓ *Please choose one of the options:*\n\n"
            "• ✅ **YES** - Submit complaint to GHMC\n"
            "• ❌ **NO** - Cancel this report\n\n"
            "_Please tap one of the buttons below._",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        return WAITING_FOR_CONFIRMATION

def cleanup_temp_files(context: ContextTypes.DEFAULT_TYPE):
    """Clean up temporary files"""
    try:
        report_data = context.user_data.get('report_data', {})
        
        # Remove image
        image_path = report_data.get('image_path')
        if image_path and os.path.exists(image_path):
            os.remove(image_path)
            logger.info(f"Cleaned up: {image_path}")
    
    except Exception as e:
        logger.error(f"Error cleaning up files: {e}")

async def handle_text_without_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages when photo is required"""
    language = context.user_data.get('language', 'en')
    messages = get_messages(language)
    
    await update.message.reply_text(
        messages.IMAGE_REQUIRED,
        parse_mode='Markdown'
    )
    return WAITING_FOR_PHOTO

async def cancel_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel the reporting process"""
    language = context.user_data.get('language', 'en')
    messages = get_messages(language)
    
    cleanup_temp_files(context)
    
    await update.message.reply_text(
        messages.REPORT_CANCELLED,
        reply_markup=ReplyKeyboardRemove()
    )
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
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_without_photo),
            ],
            WAITING_FOR_LOCATION: [
                MessageHandler(filters.LOCATION, handle_location),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_voice_or_text),
            ],
            WAITING_FOR_DETAILS: [
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