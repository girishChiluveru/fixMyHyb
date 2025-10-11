import sqlite3

def init_database():
    conn = sqlite3.connect('fixmyhyd.db')
    c = conn.cursor()
    
    # Create telegram_users table
    c.execute('''
        CREATE TABLE IF NOT EXISTS telegram_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_user_id TEXT UNIQUE NOT NULL,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            language_code TEXT DEFAULT 'en',
            phone_number TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create user_media table
    c.execute('''
        CREATE TABLE IF NOT EXISTS user_media (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_user_id TEXT NOT NULL,
            complaint_id INTEGER,
            media_type TEXT NOT NULL,
            upload_method TEXT,
            file_id TEXT NOT NULL,
            file_path TEXT,
            file_size INTEGER,
            file_name TEXT,
            mime_type TEXT,
            caption TEXT,
            preserves_exif BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (complaint_id) REFERENCES complaints (id),
            FOREIGN KEY (telegram_user_id) REFERENCES telegram_users (telegram_user_id)
        )
    ''')
    
    conn.commit()
    conn.close()
    print("Database tables created successfully")

if __name__ == '__main__':
    init_database()