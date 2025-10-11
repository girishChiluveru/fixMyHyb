#!/usr/bin/env python3
"""
Test API Client Console Logging
"""
import os
import sys

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bot.services.api_client import api_client
from config.settings import settings

def test_api_client():
    """Test the API client with console logging"""
    print("🧪 Testing API Client Console Logging")
    print("=" * 50)
    
    # Test initialization
    print(f"✅ API Client initialized")
    print(f"   Backend URL: {settings.API_BASE_URL}")
    print(f"   Google API Key: {'Configured' if settings.GOOGLE_API_KEY else 'Not configured'}")
    print()
    
    # Test text analysis (should work with fallback)
    print("🔤 Testing text analysis...")
    test_description = "There is a large pothole on the main road near my house. It's causing problems for vehicles."
    
    result = api_client.analyze_text(test_description)
    if result:
        print(f"✅ Text analysis completed")
        print(f"   Result: {result.get('issue_type', 'Unknown')}")
    else:
        print("❌ Text analysis failed")
    print()
    
    # Test image analysis (will likely use fallback since we don't have real image)
    print("🖼️  Testing image analysis (fallback mode)...")
    # Create a dummy text file for testing (since we don't have a real image)
    dummy_file = "temp_test.txt"
    try:
        with open(dummy_file, 'w') as f:
            f.write("test")
        
        # This will fail but we'll see the console logging
        result = api_client.analyze_image(dummy_file)
        print(f"   Image analysis attempted (expected to fail)")
        
    except Exception as e:
        print(f"   Expected error: {e}")
    finally:
        if os.path.exists(dummy_file):
            os.remove(dummy_file)
    
    print()
    print("🎯 Console logging test completed!")

if __name__ == "__main__":
    test_api_client()