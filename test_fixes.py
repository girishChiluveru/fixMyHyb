#!/usr/bin/env python3
"""
Test the fixes for user data saving and error handling
"""
import os
import sys
import sqlite3

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bot.services.api_client import api_client

def test_user_data_saving():
    """Test user data saving functionality"""
    print("🧪 Testing User Data Saving Functionality")
    print("=" * 50)
    
    # Test user data
    test_user = {
        'telegram_user_id': '12345678',
        'username': 'test_user',
        'first_name': 'Test',
        'last_name': 'User',
        'language_code': 'en'
    }
    
    # Test saving user data
    print("💾 Testing save_user_data method...")
    result = api_client.save_user_data(test_user)
    
    if result and result.get('status') == 'success':
        print("✅ User data saved successfully")
        print(f"   Result: {result}")
    else:
        print("❌ User data saving failed")
        print(f"   Result: {result}")
    
    # Verify data was saved by checking database
    print("\n🔍 Verifying data in database...")
    try:
        conn = sqlite3.connect('fixmyhyd.db')
        c = conn.cursor()
        
        c.execute("SELECT * FROM telegram_users WHERE telegram_user_id = ?", (test_user['telegram_user_id'],))
        user_record = c.fetchone()
        
        if user_record:
            print("✅ User found in database")
            print(f"   Record: {user_record}")
        else:
            print("❌ User not found in database")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Database verification error: {e}")
    
    print("\n🎯 User data saving test completed!")

def test_text_analysis():
    """Test text analysis functionality"""
    print("\n📝 Testing Text Analysis...")
    print("-" * 30)
    
    test_text = "There is a huge garbage pile in our colony. GHMC please clean it."
    
    result = api_client.analyze_text(test_text)
    if result:
        print("✅ Text analysis successful")
        print(f"   Category: {result.get('issue_type', 'Unknown')}")
        print(f"   Description: {result.get('description', 'N/A')[:50]}...")
    else:
        print("❌ Text analysis failed")

def check_database_setup():
    """Check if database is properly set up"""
    print("\n🗄️  Checking Database Setup...")
    print("-" * 30)
    
    try:
        conn = sqlite3.connect('fixmyhyd.db')
        c = conn.cursor()
        
        # Check if tables exist
        c.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = c.fetchall()
        
        print(f"📊 Found {len(tables)} tables:")
        for table in tables:
            print(f"   - {table[0]}")
        
        # Check telegram_users table structure
        if ('telegram_users',) in tables:
            c.execute("PRAGMA table_info(telegram_users)")
            columns = c.fetchall()
            print(f"\n👤 telegram_users table has {len(columns)} columns:")
            for col in columns:
                print(f"   - {col[1]} ({col[2]})")
        
        conn.close()
        print("✅ Database setup verified")
        
    except Exception as e:
        print(f"❌ Database check error: {e}")

if __name__ == "__main__":
    check_database_setup()
    test_user_data_saving()
    test_text_analysis()