import requests
import logging
import base64
import os
import time
from typing import Optional, Dict
from config.settings import settings
from bot.utils.debug_logger import DebugLogger
from bot.utils.fallback_analyzer import FallbackAnalyzer
import google.generativeai as genai

logger = logging.getLogger(__name__)
debug = DebugLogger(__name__)

# Initialize fallback analyzer
fallback_analyzer = FallbackAnalyzer()


class APIClient:
    """Client to interact with Gemini AI and Backend API"""
    
    def __init__(self):
        self.api_key = settings.GOOGLE_API_KEY
        self.backend_url = settings.API_BASE_URL
        self.timeout = 30  # seconds
        
        # Configure Gemini AI
        if self.api_key:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel('gemini-2.5-flash')
            debug.console_log("[API CLIENT] Gemini AI configured successfully")
        else:
            self.model = None
            debug.console_log("[API CLIENT] No API key - Gemini AI disabled")
        
        # Log initialization
        debug.console_log("[API CLIENT] Initializing API client...")
        debug.console_log(f"[API CLIENT] Backend URL: {self.backend_url}")
        if self.api_key:
            debug.console_log(f"[API CLIENT] Google API key configured: {self.api_key[:10]}...")
        else:
            debug.console_log("[API CLIENT] Warning: No Google API key configured - will use fallback analysis")
    
    # ==================== BACKEND API METHODS ====================
    
    def analyze_image(self, image_path: str) -> Optional[Dict]:
        """
        Analyze image using backend API (which uses Gemini)
        Falls back to direct Gemini AI if backend is unavailable
        
        Args:
            image_path: Path to image file
            
        Returns:
            Dict with analysis results
        """
        debug.console_log(f"[API CLIENT] 🔍 Starting image analysis: {os.path.basename(image_path)}")
        
        # First try backend API
        result = self._analyze_image_with_backend(image_path)
        if result:
            return result
        
        # Fallback to direct Gemini AI
        debug.console_log("[API CLIENT] 🔄 Backend unavailable, trying direct Gemini AI...")
        return self._analyze_image_with_gemini(image_path)
    
    def _analyze_image_with_backend(self, image_path: str) -> Optional[Dict]:
        """Analyze image using backend Gemini API"""
        debug.console_log("[API CLIENT] 🌐 Trying backend API with Gemini...")
        
        try:
            with open(image_path, 'rb') as f:
                files = {'image': f}
                
                start_time = time.time()
                response = requests.post(
                    f"{self.backend_url}/api/analyze-image",
                    files=files,
                    timeout=self.timeout
                )
                request_time = time.time() - start_time
                
                debug.console_log(f"[API CLIENT] 📡 Backend response received in {request_time:.2f}s")
                debug.console_log(f"[API CLIENT] Status Code: {response.status_code}")
                
                if response.status_code == 200:
                    result = response.json()
                    debug.console_log("[API CLIENT] ✅ Backend analysis successful")
                    
                    # Transform backend response to our format
                    if result.get('status') == 'success':
                        analysis = result.get('analysis', {})
                        transformed_result = {
                            'status': 'success',
                            'analysis': {
                                'category': analysis.get('category', 'Unknown'),
                                'summary': analysis.get('summary', 'Analysis completed'),
                                'confidence': 'high',
                                'source': 'backend_gemini'
                            }
                        }
                        
                        debug.console_log(f"[API CLIENT] 🎯 Category: {analysis.get('category', 'Unknown')}")
                        debug.console_log(f"[API CLIENT] 📝 Summary: {analysis.get('summary', 'N/A')[:50]}...")
                        return transformed_result
                else:
                    debug.console_log(f"[API CLIENT] ❌ Backend request failed: {response.status_code}")
                    debug.console_log(f"[API CLIENT] Error: {response.text[:200]}...")
                    return None
                    
        except requests.exceptions.Timeout:
            debug.console_log(f"[API CLIENT] ⏱️  Backend timeout after {self.timeout}s")
            return None
            
        except requests.exceptions.ConnectionError:
            debug.console_log("[API CLIENT] 🌐 Backend connection error")
            return None
            
        except Exception as e:
            debug.console_log(f"[API CLIENT] ❌ Backend error: {e}")
            debug.error(f"Backend API error: {e}")
            return None
    
    def analyze_text(self, description: str) -> Optional[Dict]:
        """
        Analyze text description using backend API
        
        Args:
            description: Text description from user
            
        Returns:
            Dict with analysis results
        """
        debug.console_log(f"[API CLIENT] 📝 Analyzing text: {description[:50]}...")
        
        try:
            payload = {'description': description}
            
            start_time = time.time()
            response = requests.post(
                f"{self.backend_url}/api/analyze-text",
                json=payload,
                timeout=self.timeout
            )
            request_time = time.time() - start_time
            
            debug.console_log(f"[API CLIENT] 📡 Text analysis response in {request_time:.2f}s")
            debug.console_log(f"[API CLIENT] Status Code: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                debug.console_log("[API CLIENT] ✅ Text analysis successful")
                
                if result.get('status') == 'success':
                    analysis = result.get('analysis', {})
                    debug.console_log(f"[API CLIENT] 🎯 Text category: {analysis.get('category', 'Unknown')}")
                    return {
                        'status': 'success',
                        'analysis': analysis
                    }
            else:
                debug.console_log(f"[API CLIENT] ❌ Text analysis failed: {response.status_code}")
                debug.console_log(f"[API CLIENT] Falling back to local analysis...")
                
        except Exception as e:
            debug.console_log(f"[API CLIENT] ❌ Text analysis error: {e}")
            debug.error(f"Text analysis API error: {e}")
        
        # Fallback to local analysis
        return fallback_analyzer.analyze_text(description)
    
    def transcribe_voice(self, audio_path: str) -> Optional[Dict]:
        """
        Transcribe voice using backend API
        
        Args:
            audio_path: Path to audio file
            
        Returns:
            Dict with transcription results
        """
        debug.console_log(f"[API CLIENT] 🎤 Transcribing audio: {os.path.basename(audio_path)}")
        
        try:
            with open(audio_path, 'rb') as f:
                files = {'audio': f}
                
                start_time = time.time()
                response = requests.post(
                    f"{self.backend_url}/api/transcribe-voice",
                    files=files,
                    timeout=self.timeout * 2  # Voice processing takes longer
                )
                request_time = time.time() - start_time
                
                debug.console_log(f"[API CLIENT] 📡 Voice transcription response in {request_time:.2f}s")
                debug.console_log(f"[API CLIENT] Status Code: {response.status_code}")
                
                if response.status_code == 200:
                    result = response.json()
                    debug.console_log("[API CLIENT] ✅ Voice transcription successful")
                    
                    if result.get('status') == 'success':
                        transcription = result.get('transcription', '')
                        debug.console_log(f"[API CLIENT] 📝 Transcribed: {transcription[:50]}...")
                        return result
                else:
                    debug.console_log(f"[API CLIENT] ❌ Voice transcription failed: {response.status_code}")
                    debug.console_log(f"[API CLIENT] Error: {response.text[:200]}...")
                    
        except Exception as e:
            debug.console_log(f"[API CLIENT] ❌ Voice transcription error: {e}")
            debug.error(f"Voice transcription API error: {e}")
        
        return None
    
    def generate_and_submit_report(self, report_data: Dict) -> Optional[Dict]:
        """
        Generate formal report and submit to GHMC portal
        
        Args:
            report_data: Complete report information
            
        Returns:
            Dict with submission result
        """
        debug.console_log("[API CLIENT] 📋 Generating and submitting report...")
        debug.console_log(f"[API CLIENT] Report has image: {'image_analysis' in report_data}")
        debug.console_log(f"[API CLIENT] Report has voice: {'voice_transcription' in report_data}")
        debug.console_log(f"[API CLIENT] Report has text: {'text_analysis' in report_data}")
        
        try:
            start_time = time.time()
            response = requests.post(
                f"{self.backend_url}/api/generate-report",
                json=report_data,
                timeout=self.timeout * 2  # Report generation takes longer
            )
            request_time = time.time() - start_time
            
            debug.console_log(f"[API CLIENT] 📡 Report submission response in {request_time:.2f}s")
            debug.console_log(f"[API CLIENT] Status Code: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                debug.console_log("[API CLIENT] ✅ Report submitted successfully")
                
                if result.get('status') == 'success':
                    ghmc_id = result.get('ghmc_id')
                    complaint_id = result.get('complaint_id')
                    debug.console_log(f"[API CLIENT] 🎫 GHMC ID: {ghmc_id}")
                    debug.console_log(f"[API CLIENT] 🆔 Complaint ID: {complaint_id}")
                    return result
                else:
                    debug.console_log(f"[API CLIENT] ❌ Report submission failed: {result.get('error', 'Unknown error')}")
            else:
                debug.console_log(f"[API CLIENT] ❌ Report submission failed: {response.status_code}")
                debug.console_log(f"[API CLIENT] Error: {response.text[:200]}...")
                
        except Exception as e:
            debug.console_log(f"[API CLIENT] ❌ Report submission error: {e}")
            debug.error(f"Report submission API error: {e}")
        
        return None
    
    # ==================== GEMINI AI METHODS ====================
    
    def _analyze_image_with_gemini(self, image_path: str) -> Optional[Dict]:
        """
        Analyze image using direct Gemini AI
        
        Args:
            image_path: Path to image file
            
        Returns:
            Dict with analysis results or None if failed
        """
        debug.console_log(f"[API CLIENT] 🤖 Using direct Gemini AI: {os.path.basename(image_path)}")
        
        # Check if Gemini is configured
        if not self.model:
            debug.console_log("[API CLIENT] ⚠️  Gemini AI not configured - using fallback analyzer")
            return fallback_analyzer.analyze_image(image_path)
        
        try:
            start_time = time.time()
            
            # Read and prepare image for Gemini
            debug.console_log("[API CLIENT] 📷 Loading image for Gemini...")
            from PIL import Image
            
            pil_image = Image.open(image_path)
            
            # Create prompt for municipal complaint classification
            prompt = """
            Analyze this image for municipal issues and infrastructure problems. 
            
            Classify the issue into one of these categories:
            - Open Garbage Dump: Garbage piles, waste accumulation, litter
            - Sewage Leak/Overflow: Water leaks, sewage problems, drainage issues
            - Pothole/Damaged Road: Road damage, potholes, street surface issues
            - Damaged Electrical Infrastructure: Electrical poles, wires, transformers, streetlights
            - Fallen Tree: Tree blocking roads or causing obstruction
            - Water Logging: Flooding, water accumulation on roads
            - Stray Animals: Animals on roads or public spaces
            - Other: Any other municipal issue
            
            Provide a JSON response with:
            {
                "category": "category_name", 
                "summary": "brief description of what you see",
                "confidence": 0.8,
                "priority": "High/Medium/Low",
                "description": "detailed description of the issue"
            }
            """
            
            debug.console_log("[API CLIENT] 🧠 Sending image to Gemini...")
            response = self.model.generate_content([prompt, pil_image])
            
            request_time = time.time() - start_time
            debug.console_log(f"[API CLIENT] 📡 Gemini response received in {request_time:.2f}s")
            
            if response and response.text:
                debug.console_log("[API CLIENT] ✅ Gemini analysis successful")
                
                # Try to parse JSON response
                try:
                    import json
                    # Clean the response text to extract JSON
                    response_text = response.text.strip()
                    if response_text.startswith('```json'):
                        response_text = response_text[7:-3].strip()
                    elif response_text.startswith('```'):
                        response_text = response_text[3:-3].strip()
                    
                    gemini_result = json.loads(response_text)
                    
                    debug.console_log(f"[API CLIENT] 🎯 Category: {gemini_result.get('category', 'Unknown')}")
                    debug.console_log(f"[API CLIENT] 📊 Confidence: {gemini_result.get('confidence', 0.5)}")
                    
                    # Transform to our expected format
                    return {
                        'status': 'success',
                        'analysis': {
                            'category': gemini_result.get('category', 'Other'),
                            'summary': gemini_result.get('summary', 'Image analysis completed'),
                            'confidence': gemini_result.get('confidence', 0.7),
                            'priority': gemini_result.get('priority', 'Medium'),
                            'description': gemini_result.get('description', gemini_result.get('summary', '')),
                            'source': 'gemini_direct'
                        }
                    }
                    
                except json.JSONDecodeError:
                    # If JSON parsing fails, create a structured response from text
                    debug.console_log("[API CLIENT] 📝 Parsing text response from Gemini...")
                    
                    category = "Other"
                    summary = response.text[:200] + "..." if len(response.text) > 200 else response.text
                    
                    # Try to extract category from text
                    response_lower = response.text.lower()
                    if any(word in response_lower for word in ['garbage', 'waste', 'litter', 'trash']):
                        category = "Open Garbage Dump"
                    elif any(word in response_lower for word in ['pothole', 'road', 'street', 'damaged']):
                        category = "Pothole/Damaged Road"
                    elif any(word in response_lower for word in ['sewage', 'water', 'leak', 'drainage']):
                        category = "Sewage Leak/Overflow"
                    elif any(word in response_lower for word in ['electrical', 'wire', 'pole', 'light']):
                        category = "Damaged Electrical Infrastructure"
                    elif any(word in response_lower for word in ['tree', 'fallen']):
                        category = "Fallen Tree"
                    elif any(word in response_lower for word in ['flood', 'water logging', 'waterlogging']):
                        category = "Water Logging"
                    elif any(word in response_lower for word in ['animal', 'dog', 'stray']):
                        category = "Stray Animals"
                    
                    return {
                        'status': 'success',
                        'analysis': {
                            'category': category,
                            'summary': summary,
                            'confidence': 0.6,
                            'priority': 'Medium',
                            'description': response.text,
                            'source': 'gemini_direct'
                        }
                    }
            else:
                debug.console_log("[API CLIENT] ❌ Empty response from Gemini")
                return fallback_analyzer.analyze_image(image_path)
                
        except Exception as e:
            debug.console_log(f"[API CLIENT] ❌ Gemini error: {e}")
            debug.error(f"Exception during Gemini AI analysis: {e}")
            return fallback_analyzer.analyze_image(image_path)
    
    # ==================== BACKEND REPORT SUBMISSION ====================
    
    def submit_complaint_to_backend(self, complaint_data: Dict) -> Optional[Dict]:
        """
        Submit complaint to backend API
        
        Args:
            complaint_data: Complete complaint information
            
        Returns:
            Dict with submission result
        """
        debug.console_log("[API CLIENT] � Submitting complaint to backend...")
        debug.console_log(f"[API CLIENT] Issue type: {complaint_data.get('issue_type', 'unknown')}")
        
        try:
            payload = {
                'category': complaint_data.get('issue_type', 'Other'),
                'description': complaint_data.get('description', ''),
                'location': complaint_data.get('location', ''),
                'priority': complaint_data.get('priority', 'Medium'),
                'gps_lat': complaint_data.get('latitude'),
                'gps_lng': complaint_data.get('longitude'),
                'telegram_user_id': complaint_data.get('telegram_user_id'),
                'media_files': complaint_data.get('media_files', [])
            }
            
            start_time = time.time()
            response = requests.post(
                f"{self.backend_url}/api/submit-complaint",
                json=payload,
                timeout=self.timeout
            )
            request_time = time.time() - start_time
            
            debug.console_log(f"[API CLIENT] 📡 Backend response in {request_time:.2f}s")
            debug.console_log(f"[API CLIENT] Status Code: {response.status_code}")
            
            if response.status_code in [200, 201]:
                result = response.json()
                debug.console_log("[API CLIENT] ✅ Complaint submitted successfully")
                
                report_id = result.get('complaint_id', 'unknown')
                debug.console_log(f"[API CLIENT] 🎫 Complaint ID: {report_id}")
                
                return {
                    'status': 'success',
                    'complaint_id': report_id,
                    'message': result.get('message', 'Complaint submitted successfully'),
                    'data': result
                }
            else:
                debug.console_log(f"[API CLIENT] ❌ Backend submission failed: {response.status_code}")
                debug.console_log(f"[API CLIENT] Error: {response.text[:200]}...")
                debug.error(f"Report generation failed: {response.status_code} - {response.text}")
                return None
                
        except requests.exceptions.Timeout:
            debug.console_log(f"[API CLIENT] ⏱️  Backend timeout after {self.timeout}s")
            debug.error("Backend submission timeout")
            return None
            
        except requests.exceptions.ConnectionError:
            debug.console_log("[API CLIENT] 🌐 Backend connection error")
            debug.error("Backend connection error during submission")
            return None
            
        except Exception as e:
            debug.console_log(f"[API CLIENT] ❌ Backend submission error: {e}")
            debug.error(f"Exception during backend submission: {e}")
            return None
    
    def save_user_data(self, user_data: Dict) -> Optional[Dict]:
        """
        Save user data to database
        
        Args:
            user_data: User information from Telegram
            
        Returns:
            Dict with save result
        """
        debug.console_log(f"[API CLIENT] 👤 Saving user data for: {user_data.get('username', 'Unknown')}")
        
        try:
            import sqlite3
            
            # Connect to database
            conn = sqlite3.connect('fixmyhyd.db')
            c = conn.cursor()
            
            # Insert or update user data
            c.execute('''
                INSERT OR REPLACE INTO telegram_users 
                (telegram_user_id, username, first_name, last_name, language_code, updated_at)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (
                user_data.get('telegram_user_id'),
                user_data.get('username'),
                user_data.get('first_name'),
                user_data.get('last_name'),
                user_data.get('language_code', 'en')
            ))
            
            conn.commit()
            conn.close()
            
            debug.console_log(f"[API CLIENT] ✅ User data saved successfully")
            return {
                'status': 'success',
                'message': 'User data saved successfully'
            }
            
        except Exception as e:
            debug.console_log(f"[API CLIENT] ❌ Failed to save user data: {e}")
            debug.error(f"Failed to save user data: {e}")
            return {
                'status': 'error',
                'message': f'Failed to save user data: {str(e)}'
            }


# Global instance
debug.console_log("[API CLIENT] Creating global API client instance...")
api_client = APIClient()
debug.console_log("[API CLIENT] Global API client ready")