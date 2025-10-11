"""
Fallback Image Analysis
Provides basic image analysis when the backend API is unavailable
"""
import os
from typing import Dict, Optional
try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    
from bot.utils.debug_logger import DebugLogger

debug = DebugLogger(__name__)


class FallbackImageAnalyzer:
    """Basic image analysis for when backend is unavailable"""
    
    def __init__(self):
        self.categories = [
            'Road Damage', 'Garbage Collection', 'Street Lighting', 
            'Water Supply', 'Drainage', 'Public Property', 'Other'
        ]
    
    def analyze_image_basic(self, image_path: str, caption: str = "") -> Dict:
        """
        Perform basic image analysis using filename and caption
        
        Args:
            image_path: Path to image file
            caption: User-provided caption
            
        Returns:
            Dict with basic analysis results
        """
        try:
            debug.info(f"[FALLBACK] Starting basic image analysis for {os.path.basename(image_path)}")
            
            # Get image info
            image_info = self._get_image_info(image_path)
            
            # Basic categorization based on caption
            category = self._categorize_from_text(caption)
            
            # Generate basic summary
            summary = self._generate_summary(caption, image_info)
            
            result = {
                'status': 'success',
                'source': 'fallback',
                'analysis': {
                    'category': category,
                    'summary': summary,
                    'confidence': 'low',
                    'image_info': image_info,
                    'method': 'text_analysis'
                }
            }
            
            debug.info(f"[FALLBACK] Analysis complete: {category}")
            return result
            
        except Exception as e:
            debug.error(f"[FALLBACK] Error in basic analysis: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'source': 'fallback'
            }
    
    def _get_image_info(self, image_path: str) -> Dict:
        """Get basic image information"""
        try:
            if PIL_AVAILABLE:
                with Image.open(image_path) as img:
                    return {
                        'width': img.width,
                        'height': img.height,
                        'format': img.format,
                        'mode': img.mode,
                        'size_mb': round(os.path.getsize(image_path) / (1024 * 1024), 2)
                    }
            else:
                # Fallback without PIL
                return {
                    'width': 'unknown',
                    'height': 'unknown',
                    'format': 'unknown',
                    'mode': 'unknown',
                    'size_mb': round(os.path.getsize(image_path) / (1024 * 1024), 2) if os.path.exists(image_path) else 0
                }
        except Exception as e:
            debug.warning(f"[FALLBACK] Could not get image info: {e}")
            return {
                'size_mb': round(os.path.getsize(image_path) / (1024 * 1024), 2) if os.path.exists(image_path) else 0
            }
    
    def _categorize_from_text(self, text: str) -> str:
        """Basic categorization based on text content"""
        text_lower = text.lower()
        
        # Keyword mapping for categories
        category_keywords = {
            'Road Damage': ['road', 'pothole', 'crack', 'street', 'pavement', 'asphalt', 'damaged road'],
            'Garbage Collection': ['garbage', 'trash', 'waste', 'litter', 'dirty', 'dump', 'rubbish'],
            'Street Lighting': ['light', 'lamp', 'dark', 'bulb', 'illumination', 'street light'],
            'Water Supply': ['water', 'pipe', 'leak', 'tap', 'supply', 'shortage', 'burst pipe'],
            'Drainage': ['drain', 'flood', 'water logging', 'sewage', 'overflow', 'blocked drain'],
            'Public Property': ['park', 'bench', 'fence', 'building', 'property', 'facility']
        }
        
        # Count keyword matches
        category_scores = {}
        for category, keywords in category_keywords.items():
            score = sum(1 for keyword in keywords if keyword in text_lower)
            if score > 0:
                category_scores[category] = score
        
        # Return category with highest score, or 'Other' if no matches
        if category_scores:
            return max(category_scores.items(), key=lambda x: x[1])[0]
        else:
            return 'Other'
    
    def _generate_summary(self, caption: str, image_info: Dict) -> str:
        """Generate a basic summary"""
        if caption and caption.strip():
            return f"User reported: {caption.strip()}"
        else:
            return f"Image uploaded ({image_info.get('width', 'unknown')}x{image_info.get('height', 'unknown')}) - no description provided"
    
    def analyze_image(self, image_path: str) -> Dict:
        """Analyze image using basic methods when Vision API is unavailable"""
        debug.console_log(f"[FALLBACK] Starting fallback image analysis: {os.path.basename(image_path)}")
        
        try:
            # Get image info
            image_info = self._get_image_info(image_path)
            
            # Basic categorization (general civic issue)
            category = 'general_civic_issue'
            
            # Generate basic summary
            summary = f"Image analysis completed using fallback method. File: {os.path.basename(image_path)}"
            
            result = {
                'issue_type': category,
                'confidence': 0.3,  # Low confidence for fallback
                'description': summary,
                'labels': [{'description': 'civic issue', 'score': 0.3}],
                'objects': [],
                'text_detected': None,
                'source': 'fallback',
                'image_info': image_info
            }
            
            debug.console_log(f"[FALLBACK] ✅ Analysis complete: {category}")
            return result
            
        except Exception as e:
            debug.console_log(f"[FALLBACK] ❌ Error in analysis: {e}")
            debug.error(f"Fallback analysis error: {e}")
            return self.create_fallback_response(f"Analysis failed: {str(e)}")
    
    def analyze_text(self, description: str) -> Dict:
        """Analyze text description for civic issues"""
        debug.console_log(f"[FALLBACK] Analyzing text: {description[:50]}...")
        
        try:
            # Basic categorization based on text content
            category = self._categorize_from_text(description)
            
            # Map category to issue_type
            category_mapping = {
                'Road Damage': 'road_issue',
                'Garbage Collection': 'waste_management',
                'Street Lighting': 'lighting_issue',
                'Water Supply': 'water_issue',
                'Drainage': 'water_issue',
                'Public Property': 'general_civic_issue',
                'Other': 'general_civic_issue'
            }
            
            issue_type = category_mapping.get(category, 'general_civic_issue')
            
            result = {
                'issue_type': issue_type,
                'confidence': 0.5,  # Medium confidence for text analysis
                'description': f"Text analysis: {description[:100]}",
                'labels': [{'description': category.lower(), 'score': 0.5}],
                'objects': [],
                'text_detected': description,
                'source': 'fallback_text'
            }
            
            debug.console_log(f"[FALLBACK] ✅ Text analysis complete: {issue_type}")
            return result
            
        except Exception as e:
            debug.console_log(f"[FALLBACK] ❌ Text analysis error: {e}")
            debug.error(f"Fallback text analysis error: {e}")
            return self.create_fallback_response(f"Text analysis failed: {str(e)}")
    
    def create_fallback_response(self, error_message: str) -> Dict:
        """Create a basic fallback response when everything fails"""
        debug.console_log(f"[FALLBACK] Creating fallback response: {error_message}")
        
        return {
            'issue_type': 'general_civic_issue',
            'confidence': 0.1,
            'description': f"Basic analysis only: {error_message}",
            'labels': [{'description': 'unanalyzed', 'score': 0.1}],
            'objects': [],
            'text_detected': None,
            'source': 'fallback_minimal',
            'error': error_message
        }


# Global fallback analyzer instance
fallback_analyzer = FallbackImageAnalyzer()

# Create an alias for backward compatibility
FallbackAnalyzer = FallbackImageAnalyzer