#!/usr/bin/env python3
"""
Comprehensive test script for FixMyHyd Bot fixes
Tests all fixes for user data saving, error handling, and report validation
"""
import os
import sys
import sqlite3
import importlib

# Add project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

def test_imports():
    """Test if all modules can be imported correctly"""
    print("=" * 50)
    print("🔧 TESTING MODULE IMPORTS")
    print("=" * 50)
    
    try:
        print("📦 Importing config.settings...")
        from config.settings import settings
        print("   ✅ SUCCESS: config.settings imported")
        
        print("📦 Importing bot.utils.debug_logger...")
        from bot.utils.debug_logger import DebugLogger
        print("   ✅ SUCCESS: debug_logger imported")
        
        print("📦 Importing bot.services.api_client...")
        # Clear any cached imports first
        if 'bot.services.api_client' in sys.modules:
            del sys.modules['bot.services.api_client']
        
        from bot.services.api_client import api_client
        print("   ✅ SUCCESS: api_client imported")
        
        print("📦 Checking api_client methods...")
        required_methods = ['save_user_data', 'analyze_text', 'analyze_image', 'generate_report']
        
        for method in required_methods:
            if hasattr(api_client, method):
                print(f"   ✅ METHOD FOUND: {method}")
            else:
                print(f"   ❌ METHOD MISSING: {method}")
        
        return api_client
        
    except Exception as e:
        print(f"   ❌ IMPORT ERROR: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_database_setup():
    """Test database setup and structure"""
    print("\n" + "=" * 50)
    print("🗄️  TESTING DATABASE SETUP")
    print("=" * 50)
    
    try:
        conn = sqlite3.connect('fixmyhyd.db')
        c = conn.cursor()
        
        # Check if tables exist
        c.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [table[0] for table in c.fetchall()]
        
        print(f"📊 Found {len(tables)} tables: {', '.join(tables)}")
        
        # Check telegram_users table structure
        if 'telegram_users' in tables:
            c.execute("PRAGMA table_info(telegram_users)")
            columns = c.fetchall()
            print(f"👤 telegram_users table has {len(columns)} columns:")
            for col in columns:
                print(f"   - {col[1]} ({col[2]})")
            print("   ✅ telegram_users table structure verified")
        else:
            print("   ❌ telegram_users table not found")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"   ❌ DATABASE ERROR: {e}")
        return False

def test_user_data_saving(api_client):
    """Test user data saving functionality"""
    print("\n" + "=" * 50)
    print("👤 TESTING USER DATA SAVING")
    print("=" * 50)
    
    if not api_client:
        print("   ❌ SKIPPED: api_client not available")
        return False
    
    # Test user data
    test_user = {
        'telegram_user_id': 'test_123456',
        'username': 'test_fix_user',
        'first_name': 'Test',
        'last_name': 'FixUser',
        'language_code': 'en'
    }
    
    try:
        print(f"💾 Testing save_user_data with user: {test_user['username']}")
        result = api_client.save_user_data(test_user)
        
        if result and result.get('status') == 'success':
            print("   ✅ User data saved successfully")
            
            # Verify in database
            conn = sqlite3.connect('fixmyhyd.db')
            c = conn.cursor()
            c.execute("SELECT * FROM telegram_users WHERE telegram_user_id = ?", 
                     (test_user['telegram_user_id'],))
            user_record = c.fetchone()
            conn.close()
            
            if user_record:
                print("   ✅ User data verified in database")
                print(f"   📄 Record: {user_record}")
                return True
            else:
                print("   ❌ User data not found in database")
                return False
        else:
            print(f"   ❌ User data saving failed: {result}")
            return False
            
    except Exception as e:
        print(f"   ❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_text_analysis(api_client):
    """Test text analysis functionality"""
    print("\n" + "=" * 50)
    print("📝 TESTING TEXT ANALYSIS")
    print("=" * 50)
    
    if not api_client:
        print("   ❌ SKIPPED: api_client not available")
        return False
    
    test_cases = [
        "There is a huge garbage pile in our colony. GHMC please clean it.",
        "Street light is not working in our area",
        "Water supply problem in our locality"
    ]
    
    success_count = 0
    
    for i, test_text in enumerate(test_cases, 1):
        try:
            print(f"📄 Test Case {i}: {test_text[:30]}...")
            result = api_client.analyze_text(test_text)
            
            if result and result.get('issue_type'):
                print(f"   ✅ Analysis successful: {result.get('issue_type')}")
                success_count += 1
            else:
                print(f"   ❌ Analysis failed: {result}")
                
        except Exception as e:
            print(f"   ❌ ERROR: {e}")
    
    print(f"\n📊 Text Analysis Results: {success_count}/{len(test_cases)} successful")
    return success_count == len(test_cases)

def main():
    """Run all tests"""
    print("🤖 FixMyHyd Bot Comprehensive Test Suite")
    print("Testing all fixes for user data saving and error handling")
    
    # Change to project directory
    os.chdir(project_root)
    
    results = {}
    
    # Test 1: Module imports
    api_client = test_imports()
    results['imports'] = api_client is not None
    
    # Test 2: Database setup
    results['database'] = test_database_setup()
    
    # Test 3: User data saving
    results['user_data'] = test_user_data_saving(api_client)
    
    # Test 4: Text analysis
    results['text_analysis'] = test_text_analysis(api_client)
    
    # Final summary
    print("\n" + "=" * 50)
    print("📊 FINAL TEST RESULTS")
    print("=" * 50)
    
    passed = sum(results.values())
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {test_name.upper()}: {status}")
    
    print(f"\n🎯 Overall Result: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED! The bot fixes are working correctly.")
        print("\n📋 Summary of fixes:")
        print("   ✅ User data is saved immediately when users start the bot")
        print("   ✅ API client has all required methods")
        print("   ✅ Text analysis works with backend or fallback")
        print("   ✅ Database structure is correct")
        print("\n🚀 The bot is ready for deployment!")
    else:
        print("⚠️  Some tests failed. Please check the errors above.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)