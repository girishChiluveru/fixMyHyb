import requests
import logging
import base64
import os
from typing import Optional, Dict
from config.settings import settings
from bot.utils.debug_logger import DebugLogger
from bot.utils.fallback_analyzer import FallbackAnalyzer

logger = logging.getLogger(__name__)
debug = DebugLogger(__name__)

# Initialize fallback analyzer
fallback_analyzer = FallbackAnalyzer()



class APIClient:

class APIClient:    def __init__(self):

    """Client to interact with Google Vision API"""        self.api_key = settings.GOOGLE_API_KEY

            self.vision_api_url = "https://vision.googleapis.com/v1/images:annotate"

    def __init__(self):        self.timeout = 30

        self.api_key = settings.GOOGLE_API_KEY

        self.vision_api_url = "https://vision.googleapis.com/v1/images:annotate"    def analyze_image(self, image_path: str) -> Optional[Dict]:

        self.timeout = 30  # seconds        debug.info(f"[GOOGLE API] Starting image analysis: {os.path.basename(image_path)}")

            

    def _encode_image(self, image_path: str) -> str:        if not self.api_key:

        """Encode image to base64 for Google Vision API"""            debug.error("[GOOGLE API] No API key configured")

        try:            return fallback_analyzer.analyze_image(image_path)

            with open(image_path, "rb") as image_file:        

                return base64.b64encode(image_file.read()).decode('utf-8')        return fallback_analyzer.analyze_image(image_path)

        except Exception as e:

            debug.error(f"[GOOGLE API] Failed to encode image: {e}")    def analyze_text(self, description: str) -> Optional[Dict]:

            return None        debug.info("[GOOGLE API] Analyzing text description")

            return fallback_analyzer.analyze_text(description)

    def analyze_image(self, image_path: str) -> Optional[Dict]:

        """    def save_report(self, report_data: Dict) -> Optional[Dict]:

        Send image to Google Vision API for analysis        debug.info("[GOOGLE API] Saving report data")

                return {

        Args:            'status': 'success',

            image_path: Path to image file            'report_id': f"RPT_{hash(str(report_data)) % 100000:05d}",

                        'message': 'Report saved successfully'

        Returns:        }

            Dict with analysis results or None if failed

        """# Global instance

        debug.info(f"[GOOGLE API] Starting image analysis: {os.path.basename(image_path)}")api_client = APIClient()

        
        if not self.api_key:
            debug.error("[GOOGLE API] No API key configured")
            return fallback_analyzer.analyze_image(image_path)
        
        # Encode image
        encoded_image = self._encode_image(image_path)
        if not encoded_image:
            return fallback_analyzer.analyze_image(image_path)
        
        # Prepare request payload
        payload = {
            "requests": [
                {
                    "image": {
                        "content": encoded_image
                    },
                    "features": [
                        {"type": "LABEL_DETECTION", "maxResults": 10},
                        {"type": "TEXT_DETECTION", "maxResults": 1},
                        {"type": "OBJECT_LOCALIZATION", "maxResults": 10}
                    ]
                }
            ]
        }
        
        try:
            # Make API request
            url = f"{self.vision_api_url}?key={self.api_key}"
            response = requests.post(url, json=payload, timeout=self.timeout)
            
            if response.status_code == 200:
                result = response.json()
                debug.success(f"[GOOGLE API] Image analysis successful")
                return self._parse_vision_response(result)
            else:
                debug.error(f"[GOOGLE API] Request failed: {response.status_code} - {response.text}")
                return fallback_analyzer.analyze_image(image_path)
                
        except Exception as e:
            debug.error(f"[GOOGLE API] Exception during image analysis: {e}")
            return fallback_analyzer.analyze_image(image_path)
    
    def _parse_vision_response(self, response: Dict) -> Dict:
        """Parse Google Vision API response into our format"""
        try:
            responses = response.get('responses', [])
            if not responses:
                return fallback_analyzer.create_fallback_response("No analysis data returned")
            
            vision_data = responses[0]
            
            # Extract labels (objects/concepts)
            labels = []
            label_annotations = vision_data.get('labelAnnotations', [])
            for label in label_annotations:
                labels.append({
                    'description': label.get('description', ''),
                    'score': label.get('score', 0)
                })
            
            # Extract text
            text_content = ""
            text_annotations = vision_data.get('textAnnotations', [])
            if text_annotations:
                text_content = text_annotations[0].get('description', '')
            
            # Extract objects
            objects = []
            localized_objects = vision_data.get('localizedObjectAnnotations', [])
            for obj in localized_objects:
                objects.append({
                    'name': obj.get('name', ''),
                    'score': obj.get('score', 0)
                })
            
            # Classify as civic issue
            issue_type = self._classify_civic_issue(labels, objects, text_content)
            
            # Build response
            analysis_result = {
                'issue_type': issue_type,
                'confidence': self._calculate_confidence(labels),
                'description': self._generate_description(labels, objects, text_content),
                'labels': labels[:5],  # Top 5 labels
                'objects': objects[:5],  # Top 5 objects
                'text_detected': text_content[:500] if text_content else None,
                'source': 'google_vision'
            }
            
            debug.info(f"[GOOGLE API] Classified as: {issue_type}")
            return analysis_result
            
        except Exception as e:
            debug.error(f"[GOOGLE API] Failed to parse response: {e}")
            return fallback_analyzer.create_fallback_response("Failed to parse analysis")
    
    def _classify_civic_issue(self, labels, objects, text_content) -> str:
        """Classify the civic issue type based on detected content"""
        # Convert to lists of strings for analysis
        label_descriptions = [label.get('description', '').lower() for label in labels]
        object_names = [obj.get('name', '').lower() for obj in objects]
        text_lower = text_content.lower() if text_content else ""
        
        all_content = label_descriptions + object_names + [text_lower]
        content_text = ' '.join(all_content)
        
        # Issue classification keywords
        if any(keyword in content_text for keyword in ['pothole', 'road', 'crack', 'asphalt', 'street']):
            return 'road_issue'
        elif any(keyword in content_text for keyword in ['trash', 'garbage', 'litter', 'waste', 'dump']):
            return 'waste_management'
        elif any(keyword in content_text for keyword in ['water', 'leak', 'pipe', 'drainage', 'flood']):
            return 'water_issue'
        elif any(keyword in content_text for keyword in ['light', 'lamp', 'street light', 'dark']):
            return 'lighting_issue'
        elif any(keyword in content_text for keyword in ['tree', 'branch', 'fallen', 'vegetation']):
            return 'vegetation_issue'
        elif any(keyword in content_text for keyword in ['construction', 'building', 'noise', 'dust']):
            return 'construction_issue'
        else:
            return 'general_civic_issue'
    
    def _calculate_confidence(self, labels) -> float:
        """Calculate confidence score based on label scores"""
        if not labels:
            return 0.3
        
        # Average of top 3 label scores
        top_scores = [label.get('score', 0) for label in labels[:3]]
        return sum(top_scores) / len(top_scores) if top_scores else 0.3
    
    def _generate_description(self, labels, objects, text_content) -> str:
        """Generate human-readable description"""
        description_parts = []
        
        # Add top labels
        if labels:
            top_labels = [label.get('description') for label in labels[:3]]
            description_parts.append(f"Detected: {', '.join(top_labels)}")
        
        # Add detected text if meaningful
        if text_content and len(text_content.strip()) > 3:
            clean_text = text_content.strip().replace('\n', ' ')[:100]
            description_parts.append(f"Text found: {clean_text}")
        
        return '. '.join(description_parts) if description_parts else "Image analysis completed"
    
    def analyze_text(self, description: str) -> Optional[Dict]:
        """
        Analyze text description for civic issues
        
        Args:
            description: Text description from user
            
        Returns:
            Dict with analysis results
        """
        debug.info("[GOOGLE API] Analyzing text description")
        
        # For text analysis, we'll use our fallback analyzer
        # Google Vision API is primarily for images
        return fallback_analyzer.analyze_text(description)
    
    def save_report(self, report_data: Dict) -> Optional[Dict]:
        """
        Save report data
        
        Args:
            report_data: Complete report information
            
        Returns:
            Dict with save result
        """
        debug.info("[GOOGLE API] Saving report data")
        
        # For now, just return success
        # In a real implementation, this would save to a database
        return {
            'status': 'success',
            'report_id': f"RPT_{hash(str(report_data)) % 100000:05d}",
            'message': 'Report saved successfully'
        }


# Global instance
api_client = APIClient()