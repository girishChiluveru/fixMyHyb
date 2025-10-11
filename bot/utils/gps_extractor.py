import os
import logging
from PIL import Image, ExifTags

logger = logging.getLogger(__name__)

class GPSExtractor:
    def extract_for_telegram(self, image_path: str) -> dict:
        """
        Simplified extraction method for Telegram bot use.
        Returns user-friendly result.
        """
        logger.info(f"[GPS_DEBUG] Starting GPS extraction for: {image_path}")
        result = self.extract_gps_coordinates(image_path)
        logger.info(f"[GPS_DEBUG] Extraction result: {result}")
        
        return {
            'success': result['has_gps'],
            'latitude': result.get('latitude'),
            'longitude': result.get('longitude'),
            'altitude': result.get('altitude'),
            'maps_url': f"https://www.google.com/maps?q={result.get('latitude')},{result.get('longitude')}" if result['has_gps'] else None,
            'error': result.get('error')
        }

    def extract_gps_coordinates(self, image_path: str) -> dict:
        """
        Extract GPS coordinates from image EXIF data
        """
        try:
            logger.info(f"[GPS_DEBUG] File exists: {os.path.exists(image_path)}")
            logger.info(f"[GPS_DEBUG] File size: {os.path.getsize(image_path) if os.path.exists(image_path) else 'N/A'}")
            
            # Open the image
            with Image.open(image_path) as img:
                logger.info(f"[GPS_DEBUG] Image format: {img.format}")
                logger.info(f"[GPS_DEBUG] Image size: {img.size}")
                
                # Get EXIF data
                exif_data = img._getexif()
                logger.info(f"[GPS_DEBUG] Has EXIF data: {exif_data is not None}")
                
                if not exif_data:
                    return {
                        'has_gps': False,
                        'latitude': None,
                        'longitude': None,
                        'altitude': None,
                        'error': 'No EXIF data found in image'
                    }
                
                # Look for GPS info
                gps_info = {}
                for tag, value in exif_data.items():
                    tag_name = ExifTags.TAGS.get(tag, tag)
                    if tag_name == "GPSInfo":
                        logger.info(f"[GPS_DEBUG] Found GPS Info: {value}")
                        for gps_tag_id, gps_value in value.items():
                            gps_tag_name = ExifTags.GPSTAGS.get(gps_tag_id, gps_tag_id)
                            gps_info[gps_tag_name] = gps_value
                            logger.info(f"[GPS_DEBUG] GPS {gps_tag_name}: {gps_value}")
                        break
                
                if not gps_info:
                    logger.info("[GPS_DEBUG] No GPS info found in EXIF")
                    return {
                        'has_gps': False,
                        'latitude': None,
                        'longitude': None,
                        'altitude': None,
                        'error': 'No GPS data found in image EXIF'
                    }
                
                # Convert DMS to decimal degrees
                def dms_to_dd(dms, ref):
                    """Convert degrees, minutes, seconds to decimal degrees"""
                    try:
                        dd = float(dms[0]) + float(dms[1]) / 60.0 + float(dms[2]) / 3600.0
                        if ref in ['S', 'W']:
                            dd *= -1
                        return dd
                    except (IndexError, ValueError, TypeError) as e:
                        logger.error(f"[GPS_DEBUG] Error converting DMS to DD: {e}")
                        return None
                
                # Extract latitude
                lat = None
                if 'GPSLatitude' in gps_info and 'GPSLatitudeRef' in gps_info:
                    lat = dms_to_dd(gps_info['GPSLatitude'], gps_info['GPSLatitudeRef'])
                    logger.info(f"[GPS_DEBUG] Converted latitude: {lat}")
                
                # Extract longitude
                lon = None
                if 'GPSLongitude' in gps_info and 'GPSLongitudeRef' in gps_info:
                    lon = dms_to_dd(gps_info['GPSLongitude'], gps_info['GPSLongitudeRef'])
                    logger.info(f"[GPS_DEBUG] Converted longitude: {lon}")
                
                # Extract altitude (optional)
                alt = None
                if 'GPSAltitude' in gps_info:
                    try:
                        alt = float(gps_info['GPSAltitude'])
                        logger.info(f"[GPS_DEBUG] Altitude: {alt}")
                    except (ValueError, TypeError):
                        logger.warning("[GPS_DEBUG] Could not parse altitude")
                
                if lat is not None and lon is not None:
                    logger.info(f"[GPS_DEBUG] Successfully extracted GPS: {lat}, {lon}")
                    return {
                        'has_gps': True,
                        'latitude': lat,
                        'longitude': lon,
                        'altitude': alt,
                        'error': None
                    }
                else:
                    logger.warning("[GPS_DEBUG] Could not extract valid lat/lon coordinates")
                    return {
                        'has_gps': False,
                        'latitude': None,
                        'longitude': None,
                        'altitude': None,
                        'error': 'Could not parse GPS coordinates from EXIF data'
                    }
                    
        except Exception as e:
            logger.error(f"[GPS_DEBUG] Exception during GPS extraction: {e}")
            return {
                'has_gps': False,
                'latitude': None,
                'longitude': None,
                'altitude': None,
                'error': f'Error extracting GPS: {str(e)}'
            }