"""
Session Manager for tracking user report sessions
"""
import uuid
from datetime import datetime
from typing import Dict, Optional, List
from bot.utils.debug_logger import DebugLogger

debug = DebugLogger(__name__)


class SessionManager:
    """Manages user report sessions"""
    
    def __init__(self):
        # Store sessions in memory (could be moved to database later)
        self.sessions: Dict[str, Dict] = {}  # session_id -> session_data
        self.user_sessions: Dict[str, List[str]] = {}  # user_id -> [session_ids]
        self.user_gps_cache: Dict[str, Dict] = {}  # user_id -> last_gps_data
        self.draft_complaints: Dict[str, Dict] = {}  # session_id -> draft_complaint
    
    def create_session(self, user_id: str) -> str:
        """Create a new session for a user"""
        session_id = str(uuid.uuid4())[:8]  # Short session ID
        
        session_data = {
            'session_id': session_id,
            'user_id': user_id,
            'created_at': datetime.now(),
            'status': 'active',  # active, completed, cancelled
            'data': {
                'images': [],
                'voices': [],
                'descriptions': [],
                'location': None,
                'gps_data': None,
                'ai_analysis': None
            }
        }
        
        self.sessions[session_id] = session_data
        
        # Track user sessions
        if user_id not in self.user_sessions:
            self.user_sessions[user_id] = []
        self.user_sessions[user_id].append(session_id)
        
        debug.info(f"[SESSION] Created new session {session_id} for user {user_id}")
        return session_id
    
    def get_session(self, session_id: str) -> Optional[Dict]:
        """Get session data by session ID"""
        return self.sessions.get(session_id)
    
    def get_user_active_session(self, user_id: str) -> Optional[str]:
        """Get user's current active session ID"""
        user_session_ids = self.user_sessions.get(user_id, [])
        
        # Find the latest active session
        for session_id in reversed(user_session_ids):
            session = self.sessions.get(session_id)
            if session and session['status'] == 'active':
                return session_id
        
        return None
    
    def update_session(self, session_id: str, data: Dict) -> bool:
        """Update session data"""
        if session_id not in self.sessions:
            return False
        
        session = self.sessions[session_id]
        
        # Update session data
        for key, value in data.items():
            if key in session['data']:
                if isinstance(session['data'][key], list):
                    session['data'][key].append(value)
                else:
                    session['data'][key] = value
        
        debug.info(f"[SESSION] Updated session {session_id} with {list(data.keys())}")
        return True
    
    def add_image(self, session_id: str, image_data: Dict) -> bool:
        """Add image to session"""
        return self.update_session(session_id, {'images': image_data})
    
    def add_voice(self, session_id: str, voice_data: Dict) -> bool:
        """Add voice note to session"""
        return self.update_session(session_id, {'voices': voice_data})
    
    def add_description(self, session_id: str, description: str) -> bool:
        """Add text description to session"""
        return self.update_session(session_id, {'descriptions': description})
    
    def set_location(self, session_id: str, location_data: Dict) -> bool:
        """Set location for session"""
        return self.update_session(session_id, {'location': location_data})
    
    def set_gps_data(self, session_id: str, gps_data: Dict) -> bool:
        """Set GPS data for session"""
        return self.update_session(session_id, {'gps_data': gps_data})
    
    def set_ai_analysis(self, session_id: str, analysis_data: Dict) -> bool:
        """Set AI analysis for session"""
        return self.update_session(session_id, {'ai_analysis': analysis_data})
    
    def complete_session(self, session_id: str) -> bool:
        """Mark session as completed"""
        if session_id in self.sessions:
            self.sessions[session_id]['status'] = 'completed'
            self.sessions[session_id]['completed_at'] = datetime.now()
            debug.info(f"[SESSION] Completed session {session_id}")
            return True
        return False
    
    def cancel_session(self, session_id: str) -> bool:
        """Mark session as cancelled"""
        if session_id in self.sessions:
            self.sessions[session_id]['status'] = 'cancelled'
            self.sessions[session_id]['cancelled_at'] = datetime.now()
            debug.info(f"[SESSION] Cancelled session {session_id}")
            return True
        return False
    
    def is_session_ready(self, session_id: str) -> Dict:
        """Check if session has minimum required data for submission"""
        session = self.get_session(session_id)
        if not session:
            return {'ready': False, 'missing': ['session']}
        
        data = session['data']
        missing = []
        
        # Check required data
        if not data['images']:
            missing.append('image')
        
        if not data['descriptions'] and not data['voices']:
            missing.append('description or voice note')
        
        # Location is optional but recommended
        has_location = data['location'] or data['gps_data']
        
        return {
            'ready': len(missing) == 0,
            'missing': missing,
            'has_location': has_location,
            'data_summary': {
                'images': len(data['images']),
                'voices': len(data['voices']),
                'descriptions': len(data['descriptions']),
                'has_gps': bool(data['gps_data']),
                'has_location': bool(data['location']),
                'has_ai_analysis': bool(data['ai_analysis'])
            }
        }
    
    def get_session_summary(self, session_id: str) -> str:
        """Get a human-readable summary of session data"""
        session = self.get_session(session_id)
        if not session:
            return "Session not found"
        
        data = session['data']
        
        summary_parts = []
        summary_parts.append(f"📋 *Session {session_id}*")
        summary_parts.append(f"📸 Images: {len(data['images'])}")
        summary_parts.append(f"🎤 Voice notes: {len(data['voices'])}")
        summary_parts.append(f"✍️ Descriptions: {len(data['descriptions'])}")
        
        if data['gps_data']:
            summary_parts.append("📍 GPS: Available")
        elif data['location']:
            summary_parts.append("📍 Location: Available")
        else:
            summary_parts.append("📍 Location: Not available")
        
        if data['ai_analysis']:
            category = data['ai_analysis'].get('category', 'Unknown')
            summary_parts.append(f"🤖 AI Category: {category}")
        
        return "\n".join(summary_parts)
    
    def cache_user_gps(self, user_id: str, gps_data: Dict):
        """Cache GPS coordinates for user to avoid asking repeatedly"""
        self.user_gps_cache[user_id] = {
            'latitude': gps_data.get('latitude'),
            'longitude': gps_data.get('longitude'),
            'altitude': gps_data.get('altitude'),
            'cached_at': datetime.now(),
            'maps_url': gps_data.get('maps_url')
        }
        debug.info(f"[SESSION] Cached GPS for user {user_id}: {gps_data.get('latitude')}, {gps_data.get('longitude')}")
    
    def get_cached_gps(self, user_id: str) -> Optional[Dict]:
        """Get cached GPS coordinates for user"""
        cached_gps = self.user_gps_cache.get(user_id)
        if cached_gps:
            debug.info(f"[SESSION] Using cached GPS for user {user_id}")
            return cached_gps
        return None
    
    def save_draft_complaint(self, session_id: str, complaint_data: Dict):
        """Save draft complaint for GHMC submission"""
        self.draft_complaints[session_id] = {
            'session_id': session_id,
            'created_at': datetime.now(),
            'complaint_data': complaint_data,
            'status': 'draft'
        }
        debug.info(f"[SESSION] Saved draft complaint for session {session_id}")
    
    def get_draft_complaint(self, session_id: str) -> Optional[Dict]:
        """Get draft complaint by session ID"""
        return self.draft_complaints.get(session_id)
    
    def print_complaint_summary(self, session_id: str, complaint_data: Dict):
        """Print detailed complaint summary to console"""
        print("\n" + "="*60)
        print("🏛️  NEW GHMC COMPLAINT SUBMITTED")
        print("="*60)
        
        # Session info
        session = self.get_session(session_id)
        if session:
            print(f"📋 Session ID: {session_id}")
            print(f"👤 User ID: {session['user_id']}")
            print(f"⏰ Created: {session['created_at'].strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Complaint details
        print(f"\n📝 COMPLAINT DETAILS:")
        print(f"   Category: {complaint_data.get('issue_type', 'Unknown')}")
        print(f"   Priority: {complaint_data.get('priority', 'Medium')}")
        print(f"   Subject: {complaint_data.get('subject', 'No subject')}")
        
        # Description
        description = complaint_data.get('description', 'No description')
        if len(description) > 100:
            print(f"   Description: {description[:100]}...")
        else:
            print(f"   Description: {description}")
        
        # Location info
        print(f"\n📍 LOCATION:")
        if complaint_data.get('latitude') and complaint_data.get('longitude'):
            print(f"   GPS: {complaint_data['latitude']}, {complaint_data['longitude']}")
            if complaint_data.get('maps_url'):
                print(f"   Maps: {complaint_data['maps_url']}")
        
        location_text = complaint_data.get('location', 'Not provided')
        print(f"   Address: {location_text}")
        
        # Media info
        print(f"\n📎 ATTACHMENTS:")
        media_files = complaint_data.get('media_files', [])
        if media_files:
            for i, media in enumerate(media_files, 1):
                print(f"   {i}. {media.get('type', 'Unknown')}: {media.get('filename', 'N/A')}")
        else:
            print("   No attachments")
        
        # AI Analysis
        if complaint_data.get('ai_analysis'):
            ai = complaint_data['ai_analysis']
            print(f"\n🤖 AI ANALYSIS:")
            print(f"   Category: {ai.get('category', 'Unknown')}")
            print(f"   Confidence: {ai.get('confidence', 0):.2f}")
            print(f"   Source: {ai.get('source', 'Unknown')}")
        
        print("="*60)
        print("✅ Complaint logged successfully!\n")


# Global session manager instance
session_manager = SessionManager()