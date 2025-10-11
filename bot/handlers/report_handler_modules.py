"""
Modular components for report handler to break down the large functions
"""
import os
import logging
from datetime import datetime
from telegram import Update, ReplyKeyboardRemove
from telegram.ext import ContextTypes
from bot.utils.debug_logger import DebugLogger
from bot.utils.session_manager import session_manager
from bot.services.api_client import APIClient
from config.settings import settings

logger = logging.getLogger(__name__)
debug = DebugLogger(__name__)
api_client = APIClient()

class ImageProcessor:
    """Handle image processing and analysis"""
    
    @staticmethod
    async def download_and_store_image(update: Update, context: ContextTypes.DEFAULT_TYPE, file_info, is_document: bool):
        """Download image and store metadata"""
        session_id = context.user_data.get('session_id')
        user = update.effective_user
        caption = update.message.caption or ""
        
        # Download file
        file = await context.bot.get_file(file_info.file_id)
        file_extension = ".jpg"
        if is_document and hasattr(file_info, 'file_name') and file_info.file_name:
            file_extension = os.path.splitext(file_info.file_name)[1] or ".jpg"
        
        file_path = os.path.join(settings.TEMP_DIR, f"{file_info.file_id}{file_extension}")
        await file.download_to_drive(file_path)
        
        # Store image data in session
        image_data = {
            'type': 'image',
            'upload_method': 'document' if is_document else 'photo',
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
        
        # Store in report_data for compatibility
        if 'report_data' not in context.user_data:
            context.user_data['report_data'] = {}
        
        context.user_data['report_data'].update({
            'image_path': file_path,
            'caption': caption,
            'telegram_user_id': str(user.id),
            'upload_type': 'document' if is_document else 'photo',
            'session_id': session_id
        })
        
        return file_path, caption

    @staticmethod
    async def process_ai_analysis(file_path: str, filename: str, session_id: str, context: ContextTypes.DEFAULT_TYPE):
        """Process AI analysis of the image"""
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
            
            return {
                'success': True,
                'category': category,
                'summary': summary,
                'source': source,
                'analysis_data': analysis_data
            }
        
        return {'success': False, 'error': 'AI analysis failed'}

class LocationHandler:
    """Handle GPS and location processing"""
    
    @staticmethod
    async def extract_gps_from_image(file_path: str, user_id: str, session_id: str, context: ContextTypes.DEFAULT_TYPE):
        """Extract GPS from image and cache it"""
        if not settings.ENABLE_GPS_EXTRACTION:
            return {'success': False, 'reason': 'GPS extraction disabled'}
        
        from bot.utils.gps_extractor import GPSExtractor
        gps_extractor = GPSExtractor()
        gps_result = gps_extractor.extract_for_telegram(file_path)
        
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
            
            context.user_data['report_data'].update({
                'gps_lat': gps_result['latitude'],
                'gps_lng': gps_result['longitude'],
                'has_gps': True
            })
            
            return {
                'success': True,
                'latitude': gps_result['latitude'],
                'longitude': gps_result['longitude'],
                'maps_url': gps_result['maps_url']
            }
        else:
            # Check for cached GPS
            cached_gps = session_manager.get_cached_gps(user_id)
            if cached_gps:
                context.user_data['report_data'].update({
                    'gps_lat': cached_gps['latitude'],
                    'gps_lng': cached_gps['longitude'],
                    'has_gps': True
                })
                return {
                    'success': True,
                    'cached': True,
                    'latitude': cached_gps['latitude'],
                    'longitude': cached_gps['longitude'],
                    'maps_url': cached_gps['maps_url']
                }
            
            context.user_data['report_data']['has_gps'] = False
            return {
                'success': False,
                'error': gps_result.get('error', 'Unknown'),
                'no_cache': True
            }

class SubmissionHandler:
    """Handle complaint submission process"""
    
    @staticmethod
    async def prepare_submission_payload(report_data: dict):
        """Prepare payload for submission"""
        text_analysis = report_data.get('text_analysis')
        
        if not text_analysis and report_data.get('caption'):
            debug.console_log("[REPORT HANDLER] 📝 Creating text analysis from caption...")
            try:
                caption_analysis = api_client.analyze_text(report_data.get('caption'))
                if caption_analysis and caption_analysis.get('status') == 'success':
                    text_analysis = caption_analysis.get('analysis', {})
                    debug.console_log(f"[REPORT HANDLER] ✅ Caption analysis: {text_analysis.get('category', 'Unknown')}")
                else:
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
        
        return {
            'image_analysis': report_data.get('image_analysis'),
            'voice_transcription': report_data.get('voice_transcription'),
            'text_analysis': text_analysis,
            'location_text': report_data.get('caption', ''),
            'gps_lat': report_data.get('gps_lat'),
            'gps_lng': report_data.get('gps_lng'),
            'telegram_user_id': report_data.get('telegram_user_id'),
            'media_files': report_data.get('media_files', [])
        }
    
    @staticmethod
    def create_draft_complaint(report_data: dict, text_analysis: dict):
        """Create draft complaint for GHMC"""
        return {
            'issue_type': text_analysis.get('category', 'Other') if text_analysis else 'Other',
            'priority': 'Medium',
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

class UserInputHandler:
    """Handle user input validation and processing"""
    
    @staticmethod
    def is_confirmation_response(text: str) -> bool:
        """Check if text is a confirmation response"""
        confirm_keywords = ['confirm', 'submit', '✅', 'yes', 'y', 'ok', 'proceed', 'sure']
        return any(keyword in text.lower() for keyword in confirm_keywords)
    
    @staticmethod
    def is_cancellation_response(text: str) -> bool:
        """Check if text is a cancellation response"""
        cancel_keywords = ['cancel', 'no', 'stop', 'abort', '❌', 'quit']
        return any(keyword in text.lower() for keyword in cancel_keywords)
    
    @staticmethod
    def clean_user_description(text: str) -> str:
        """Clean and validate user description"""
        # Remove extra whitespace and ensure reasonable length
        cleaned = text.strip()
        if len(cleaned) > 1000:
            cleaned = cleaned[:1000] + "..."
        return cleaned

class ResponseFormatter:
    """Format responses to users"""
    
    @staticmethod
    def format_gps_success_message(gps_result: dict, upload_type: str) -> str:
        """Format GPS success message"""
        if gps_result.get('cached'):
            return (
                f"✅ *{upload_type.title()} processed successfully!*\n\n"
                f"📍 *Using Previously Saved Location*\n"
                f"Lat: {gps_result['latitude']:.6f}\n"
                f"Lon: {gps_result['longitude']:.6f}\n\n"
                f"[📍 View on Map]({gps_result['maps_url']})\n\n"
                f"💡 *Location from previous session*"
            )
        else:
            return (
                f"✅ *{upload_type.title()} processed successfully!*\n\n"
                f"📍 *GPS Location Found & Cached:*\n"
                f"Lat: {gps_result['latitude']:.6f}\n"
                f"Lon: {gps_result['longitude']:.6f}\n\n"
                f"[📍 View on Map]({gps_result['maps_url']})\n\n"
                f"💡 *Location saved for future reports*"
            )
    
    @staticmethod
    def format_ai_analysis_message(analysis_result: dict) -> str:
        """Format AI analysis result message"""
        response_text = (
            f"🤖 *AI Analysis Complete*\n\n"
            f"*🏷️ Category:* {analysis_result['category']}\n"
            f"*📝 Summary:* {analysis_result['summary']}\n"
        )
        
        if analysis_result['source'] == 'fallback':
            response_text += f"*⚠️ Source:* Offline analysis (backend unavailable)\n"
        
        return response_text
    
    @staticmethod
    def format_confirmation_message(report_data: dict) -> str:
        """Format confirmation message"""
        image_data = report_data.get('image_analysis', {})
        text_data = report_data.get('text_analysis', {})
        
        category = text_data.get('category') or image_data.get('category', 'Other')
        priority = text_data.get('priority', 'Medium')
        summary = text_data.get('summary') or image_data.get('summary', 'Issue detected')
        location_text = "GPS Available" if report_data.get('has_gps') else "No GPS"
        
        return (
            f"📋 *Complaint Summary*\n\n"
            f"*Category:* {category}\n"
            f"*Priority:* {priority}\n"
            f"*Description:* {summary}\n"
            f"*Location:* {location_text}\n\n"
            f"*Ready to submit to GHMC?*\n"
            f"Type 'yes' to confirm or 'no' to cancel."
        )