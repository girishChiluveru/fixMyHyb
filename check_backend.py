#!/usr/bin/env python3
"""
Backend Health Checker
Quick script to test if the Flask backend is running and responsive
"""
import requests
import sys
from config.settings import settings

def check_backend():
    """Check backend health and endpoints"""
    base_url = settings.API_BASE_URL
    
    print(f"🔍 Checking backend at: {base_url}")
    print("=" * 50)
    
    # Test basic connectivity
    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        print(f"✅ Health check: {response.status_code} - {response.text[:100]}")
    except requests.exceptions.ConnectionError:
        print(f"❌ Health check: Connection refused")
        print(f"   💡 Make sure Flask backend is running on {base_url}")
        return False
    except Exception as e:
        print(f"❌ Health check: {e}")
        return False
    
    # Test specific endpoints
    endpoints = [
        ("GET", "/", "Root endpoint"),
        ("POST", "/api/analyze-image", "Image analysis"),
        ("POST", "/api/transcribe-voice", "Voice transcription"),
        ("GET", "/api/users", "User management"),
    ]
    
    print("\n📡 Testing API endpoints:")
    for method, endpoint, description in endpoints:
        try:
            url = f"{base_url}{endpoint}"
            if method == "GET":
                response = requests.get(url, timeout=5)
            else:
                # For POST, just check if endpoint exists (will return 400/422 for missing data)
                response = requests.post(url, timeout=5)
            
            if response.status_code in [200, 400, 422, 405]:  # Expected responses
                print(f"✅ {description}: Available ({response.status_code})")
            else:
                print(f"⚠️ {description}: Unexpected status {response.status_code}")
        except requests.exceptions.ConnectionError:
            print(f"❌ {description}: Connection failed")
        except Exception as e:
            print(f"❌ {description}: {str(e)[:50]}")
    
    return True

def test_image_analysis():
    """Test image analysis endpoint with a dummy request"""
    print("\n🖼️ Testing image analysis endpoint:")
    
    try:
        # Try to post without image (should return 400)
        response = requests.post(f"{settings.API_BASE_URL}/api/analyze-image", timeout=5)
        
        if response.status_code == 400:
            print("✅ Image analysis endpoint is responding (expects image file)")
        elif response.status_code == 404:
            print("❌ Image analysis endpoint not found (404)")
        elif response.status_code == 500:
            print("❌ Image analysis endpoint has server error (500)")
            print(f"   Response: {response.text[:200]}")
        else:
            print(f"⚠️ Unexpected response: {response.status_code}")
            print(f"   Response: {response.text[:200]}")
            
    except Exception as e:
        print(f"❌ Error testing image analysis: {e}")

if __name__ == "__main__":
    print("🩺 FixMyHyd Backend Health Checker")
    print()
    
    if check_backend():
        test_image_analysis()
        print(f"\n📋 Summary:")
        print(f"   - Backend URL: {settings.API_BASE_URL}")
        print(f"   - If image analysis fails with 500 error:")
        print(f"     • Check Flask backend logs")
        print(f"     • Verify AI model is loaded")
        print(f"     • Check API key configurations")
        print(f"   - Bot will use fallback analysis if backend fails")
    else:
        print(f"\n❌ Backend not accessible at {settings.API_BASE_URL}")
        print(f"   💡 To fix:")
        print(f"     • Start your Flask backend server")
        print(f"     • Check if port 5001 is available")
        print(f"     • Verify API_BASE_URL in .env file")
        sys.exit(1)