"""
Debug Logger Utility
Provides clean debug messages with toggle functionality
"""
import logging
from config.settings import settings


class DebugLogger:
    """Clean debug logger with console toggle"""
    
    def __init__(self, module_name: str):
        self.logger = logging.getLogger(module_name)
        self.debug_enabled = getattr(settings, 'DEBUG_CONSOLE', True)
    
    def user_joined(self, username: str, user_id: str):
        """Log when a new user joins"""
        if self.debug_enabled:
            print(f"[NEW USER] @{username or 'Unknown'} (ID: {user_id})")
    
    def user_saved_to_db(self, username: str):
        """Log when user data is saved to database"""
        if self.debug_enabled:
            print(f"[DB SAVE] User saved: @{username or 'Unknown'}")
    
    def file_uploaded(self, filename: str, upload_type: str):
        """Log when user uploads a file"""
        if self.debug_enabled:
            print(f"[FILE UPLOAD] {filename} (Type: {upload_type})")
    
    def ai_analysis_started(self, filename: str):
        """Log when AI analysis starts"""
        if self.debug_enabled:
            print(f"[AI START] Analysis started for: {filename}")
    
    def ai_analysis_completed(self, category: str, filename: str):
        """Log when AI analysis completes"""
        if self.debug_enabled:
            print(f"[AI COMPLETE] {category} - {filename}")
    
    def gps_extracted(self, lat: float, lng: float, filename: str):
        """Log when GPS is extracted"""
        if self.debug_enabled:
            print(f"[GPS SUCCESS] {filename}: {lat:.6f}, {lng:.6f}")
    
    def gps_extraction_failed(self, reason: str, filename: str):
        """Log when GPS extraction fails"""
        if self.debug_enabled:
            print(f"[GPS FAILED] {filename}: {reason}")
    
    def report_submitted(self, report_id: str, category: str):
        """Log when report is submitted"""
        if self.debug_enabled:
            print(f"[REPORT SUBMITTED] {report_id} (Category: {category})")
    
    def voice_transcription_started(self, filename: str):
        """Log when voice transcription starts"""
        if self.debug_enabled:
            print(f"[VOICE START] Transcription started: {filename}")
    
    def voice_transcription_completed(self, filename: str):
        """Log when voice transcription completes"""
        if self.debug_enabled:
            print(f"[VOICE COMPLETE] Transcription completed: {filename}")
    
    def error(self, message: str):
        """Log errors"""
        if self.debug_enabled:
            print(f"[ERROR] {message}")
        # Always log errors to file
        self.logger.error(message)
    
    def warning(self, message: str):
        """Log warnings"""
        if self.debug_enabled:
            print(f"[WARNING] {message}")
        # Always log warnings to file
        self.logger.warning(message)
    
    def info(self, message: str):
        """Log info messages (only to file, not console)"""
        self.logger.info(message)
    
    def console_log(self, message: str):
        """Log messages to console when debug is enabled"""
        if self.debug_enabled:
            try:
                print(message)
            except UnicodeEncodeError:
                # Replace problematic Unicode characters for Windows console
                safe_message = message.encode('ascii', 'replace').decode('ascii')
                print(safe_message)
    
    def success(self, message: str):
        """Log success messages"""
        if self.debug_enabled:
            try:
                print(f"[SUCCESS] {message}")
            except UnicodeEncodeError:
                # Replace problematic Unicode characters for Windows console
                safe_message = message.encode('ascii', 'replace').decode('ascii')
                print(f"[SUCCESS] {safe_message}")
        # Also log to file
        self.logger.info(message)