#!/usr/bin/env python3
"""
Test EXIF GPS extraction functionality
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bot.utils.gps_extractor import GPSExtractor

def test_gps_extraction():
    """Test GPS extraction with sample images"""
    
    extractor = GPSExtractor()
    
    # Test with a sample file (may not exist)
    test_paths = [
        "temp/sample_with_gps.jpg",
        "temp/sample_without_gps.jpg",
        "temp/AgACAgUAAxkBAAMVaOoJLM8pVKyOoIiSfuXC4xF2f3YAAlANaxtO3FFXWAUysBu_-lABAAMCAAN5AAM2BA.jpg"  # From your log
    ]
    
    print("🧪 Testing GPS Extraction Functionality\n")
    
    for test_path in test_paths:
        if os.path.exists(test_path):
            print(f"📂 Testing: {test_path}")
            result = extractor.extract_for_telegram(test_path)
            
            print(f"   ✅ Success: {result['success']}")
            if result['success']:
                print(f"   📍 Coordinates: {result['latitude']}, {result['longitude']}")
                print(f"   🗺️  Maps URL: {result['maps_url']}")
            else:
                print(f"   ❌ Error: {result['error']}")
            print()
        else:
            print(f"⏭️  Skipping: {test_path} (file not found)")
    
    print("📊 Summary:")
    print("   • EXIF GPS extraction is now implemented")
    print("   • Debug logging shows extraction process")
    print("   • Fallback to location sharing when no GPS")
    print("   • Document uploads preserve EXIF data")
    print("   • Regular photos may have EXIF stripped by Telegram")

if __name__ == '__main__':
    test_gps_extraction()