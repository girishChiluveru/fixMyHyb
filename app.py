# app.py
import os
import json
import sqlite3
import random
from datetime import datetime, timedelta
# --- ADDED: render_template_string for the new location route ---
from flask import Flask, request, jsonify, render_template_string
from PIL import Image, ExifTags
from dotenv import load_dotenv

import google.generativeai as genai

# ==================== 1. INITIALIZATION ====================

load_dotenv()
app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False

try:
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY environment variable not set!")
    genai.configure(api_key=api_key)
    # --- BEGIN: Check Gemini API Key validity ---
    print(f"[DEBUG] GOOGLE_API_KEY loaded: {'Yes' if api_key else 'No'}")
    try:
        model = genai.GenerativeModel('gemini-pro-latest')
        test_response = model.generate_content("Say hello as JSON: {\"hello\": \"world\"}")
        print(f"[DEBUG] Gemini API test response: {test_response.text}")
    except Exception as test_e:
        print(f"[WARNING] Gemini API key test failed (this is OK for development): {test_e}")
        print("[INFO] The API key will be tested when actual requests are made")
    # --- END: Check Gemini API Key validity ---
except Exception as e:
    print(f"FATAL: Error configuring Google API: {e}")

COMPLAINT_CATEGORIES = [
    "Open Garbage Dump", "Sewage Leak/Overflow", "Pothole/Damaged Road",
    "Damaged Electrical Infrastructure", "Fallen Tree", "Water Logging",
    "Stray Animals", "Other"
]

# ==================== 2. DATABASE SETUP ====================
# (No changes in this section)
def get_db_connection():
    conn = sqlite3.connect('fixmyhyd.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_database():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS complaints (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ghmc_id TEXT UNIQUE NOT NULL,
            category TEXT NOT NULL,
            priority TEXT DEFAULT 'Medium',
            subject TEXT NOT NULL,
            description TEXT NOT NULL,
            location TEXT,
            zone TEXT,
            gps_lat REAL,
            gps_lng REAL,
            status TEXT DEFAULT 'Submitted',
            submitted_by TEXT DEFAULT 'Citizen',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS status_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            complaint_id INTEGER,
            old_status TEXT,
            new_status TEXT,
            changed_by TEXT,
            comments TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (complaint_id) REFERENCES complaints (id)
        )
    ''')
    # NEW: User data storage for telegram users
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
    # NEW: Store user media files (images, audio)
    c.execute('''
        CREATE TABLE IF NOT EXISTS user_media (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_user_id TEXT NOT NULL,
            complaint_id INTEGER,
            media_type TEXT NOT NULL, -- 'image', 'audio', 'voice'
            upload_method TEXT, -- 'photo', 'document'
            file_id TEXT NOT NULL, -- Telegram file_id
            file_path TEXT, -- Local file path
            file_size INTEGER,
            file_name TEXT, -- Original filename (for documents)
            mime_type TEXT, -- MIME type
            caption TEXT,
            preserves_exif BOOLEAN DEFAULT 0, -- Whether upload method preserves EXIF
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (complaint_id) REFERENCES complaints (id),
            FOREIGN KEY (telegram_user_id) REFERENCES telegram_users (telegram_user_id)
        )
    ''')
    conn.commit()
    conn.close()

# ==================== 3. AI HELPER FUNCTIONS (GEMINI) ====================
# (No changes in this section)
def analyze_image_with_gemini(image_stream):
    try:
        image_bytes = image_stream.read()
        image_part = {"mime_type": "image/jpeg", "data": image_bytes}
        prompt = f"""
        Analyze the image of a civic issue in Hyderabad, India. Provide a response in a valid JSON object with two keys:
        1. "summary": A brief, one-sentence summary of the scene.
        2. "category": Classify the issue into one of these exact categories: {', '.join(COMPLAINT_CATEGORIES)}.
        Example: {{"summary": "A large pothole filled with water on a city road.", "category": "Pothole/Damaged Road"}}
        """
        model = genai.GenerativeModel('gemini-pro-latest')
        response = model.generate_content([prompt, image_part])
        # print(response)
        response_text = response.text.strip().replace("json", "").replace("", "")
        
        return json.loads(response_text)
    except Exception as e:
        print(f"Error in analyze_image_with_gemini: {e}")
        return None

def transcribe_audio_with_gemini(audio_file):
    try:
        prompt = """
        You are an audio transcription service for GHMC, the civic body of Hyderabad.
        Transcribe the following audio complaint. Focus on capturing the core issue.
        Local context terms: GHMC, Hyderabad, Banjara Hills, Jubilee Hills, KBR Park, pothole, kachra, manhole, nala, street light.
        Return ONLY the transcribed text.
        """
        uploaded_file = genai.upload_file(path=audio_file, display_name="user_complaint_audio")
        model = genai.GenerativeModel('gemini-pro-latest')
        response = model.generate_content([prompt, uploaded_file])
        genai.delete_file(uploaded_file.name) # Clean up the uploaded file
        return {"transcription": response.text}
    except Exception as e:
        print(f"Error in transcribe_audio_with_gemini: {e}")
        return {"transcription": "Demonstration fallback: Could not process audio file via API."}

import re

def analyze_text_with_gemini(description):
    try:
        prompt = f"""
        Analyze the following user-submitted civic complaint. Provide a response in a valid JSON object with four keys:
        1. "category": Classify the issue into one of these exact categories: {', '.join(COMPLAINT_CATEGORIES)}.
        2. "priority": Assess the priority as 'Low', 'Medium', or 'High'.
        3. "summary": Create a succinct, one-sentence summary of the core problem.
        4. "actionable_steps": Suggest 2-3 brief, actionable steps for the municipal team.
        Complaint: "{description}"
        """
        model = genai.GenerativeModel('gemini-pro-latest')
        # Use correct SDK call
        response = model.generate_content({
            "parts": [{"text": prompt}]
        })
        response_text = response.text.strip()

        # Remove ```json and ``` if present
        response_text = re.sub(r"```json|```", "", response_text, flags=re.IGNORECASE).strip()

        # Optional: fallback if empty
        if not response_text:
            return {
                "category": "Other",
                "priority": "Medium",
                "summary": "Could not analyze text",
                "actionable_steps": ["Manually review complaint"]
            }

        return json.loads(response_text)

    except Exception as e:
        print(f"Error in analyze_text_with_gemini: {e}")
        return None


def generate_formal_report_with_gemini(data):
    try:
        prompt = f"""
        You are an AI assistant for the GHMC, creating an official complaint report.
        Synthesize the following information into a structured, formal complaint.
        The final output must be a single, valid JSON object with the keys: "subject", "description", and "zone".
        Contextual Information:
        - Image Analysis: {data.get('image_analysis')}
        - Voice Transcription: {data.get('voice_transcription')}
        - Text Analysis: {data.get('text_analysis')}
        - Location Text: {data.get('location_text', 'Not provided')}
        Instructions:
        1. "subject": Create a concise and formal subject line.
        2. "description": Write a clear, professional paragraph summarizing the entire issue.
        3. "zone": Based on the location text, identify the most likely GHMC zone (e.g., Banjara Hills, Jubilee Hills, etc.). If uncertain, state "Unknown".
        """
        model = genai.GenerativeModel('gemini-pro-latest')
        response = model.generate_content(prompt)
        response_text = response.text.strip().replace("json", "").replace("", "")
        return json.loads(response_text)
    except Exception as e:
        print(f"Error in generate_formal_report_with_gemini: {e}")
        return None

# ==================== 4. UTILITY FUNCTIONS ====================
# (No changes in this section)
def get_gps_coordinates(image_stream):
    try:
        img = Image.open(image_stream)
        exif_data = img._getexif()
        if not exif_data: return None
        gps_info = {}
        for tag, value in exif_data.items():
            tag_name = ExifTags.TAGS.get(tag, tag)
            if tag_name == "GPSInfo":
                for gps_tag_id, gps_value in value.items():
                    gps_tag_name = ExifTags.GPSTAGS.get(gps_tag_id, gps_tag_id)
                    gps_info[gps_tag_name] = gps_value
                break
        if not gps_info: return None
        def dms_to_dd(dms, ref):
            dd = dms[0] + dms[1] / 60.0 + dms[2] / 3600.0
            if ref in ['S', 'W']: dd *= -1
            return dd
        lat = dms_to_dd(gps_info['GPSLatitude'], gps_info['GPSLatitudeRef'])
        lon = dms_to_dd(gps_info['GPSLongitude'], gps_info['GPSLongitudeRef'])
        return {"latitude": lat, "longitude": lon}
    except Exception:
        return None

# ==================== 5. AI ANALYSIS ENDPOINTS ====================
# (No changes in this section)
@app.route('/api/analyze-image', methods=['POST'])
def analyze_image_endpoint():
    if 'image' not in request.files:
        return jsonify({"error": "No image file provided"}), 400
    file = request.files['image']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    gps_coords = get_gps_coordinates(file.stream)
    file.stream.seek(0)
    image_analysis = analyze_image_with_gemini(file.stream)
    if not image_analysis:
        return jsonify({"error": "Failed to analyze image with AI model"}), 500
    return jsonify({
        "status": "success",
        "analysis": image_analysis,
        "location": {"gps_coordinates": gps_coords or "Not available"}
    })

@app.route('/api/transcribe-voice', methods=['POST'])
def transcribe_voice_endpoint():
    if 'audio' not in request.files:
        return jsonify({"error": "No audio file provided"}), 400
    audio_file = request.files['audio']
    if audio_file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    temp_path = os.path.join("/tmp", audio_file.filename)
    audio_file.save(temp_path)
    transcription = transcribe_audio_with_gemini(temp_path)
    os.remove(temp_path)
    if not transcription:
        return jsonify({"error": "Failed to transcribe audio"}), 500
    return jsonify({"status": "success", "transcription": transcription.get("transcription")})

@app.route('/api/analyze-text', methods=['POST'])
def analyze_text_endpoint():
    data = request.get_json()
    if not data or 'description' not in data:
        return jsonify({"error": "Missing 'description' in request body"}), 400
    analysis = analyze_text_with_gemini(data['description'])
    if not analysis:
        return jsonify({"error": "Failed to analyze text with AI model"}), 500
    return jsonify({"status": "success", "analysis": analysis})

# ==================== 6. REPORT GENERATION & SUBMISSION ENDPOINT ====================

@app.route('/api/generate-report', methods=['POST'])
def generate_and_save_report():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON payload"}), 400

    # --- NEW: Stricter validation ---
    has_image = data.get('image_analysis')
    has_voice = data.get('voice_transcription')
    has_text = data.get('text_analysis')

    if not has_image:
        return jsonify({"error": "Validation failed: Image analysis is mandatory."}), 400
    
    if not has_voice and not has_text:
        return jsonify({"error": "Validation failed: Either voice or text description is mandatory."}), 400
    # --- END of new validation ---

    formal_report = generate_formal_report_with_gemini(data)
    if not formal_report:
        return jsonify({"error": "Failed to generate formal report with AI"}), 500

    final_category = data.get("text_analysis", {}).get("category", data.get("image_analysis", {}).get("category", "Other"))
    final_priority = data.get("text_analysis", {}).get("priority", "Medium")
    
    # NEW: Get user info for tracking
    telegram_user_id = data.get('telegram_user_id', 'Anonymous')
    
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        ghmc_id = f"GHMC/HYD/{int(datetime.now().timestamp())}"
        cursor.execute(
            """
            INSERT INTO complaints (ghmc_id, category, priority, subject, description, location, zone, gps_lat, gps_lng, submitted_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ghmc_id, final_category, final_priority,
                formal_report.get('subject', 'Untitled Complaint'),
                formal_report.get('description', 'No description generated.'),
                data.get('location_text'), formal_report.get('zone', 'Unknown'),
                data.get('gps_lat'), data.get('gps_lng'), telegram_user_id
            )
        )
        complaint_id = cursor.lastrowid
        
        # NEW: Store media files linked to this complaint
        if data.get('media_files'):
            for media in data['media_files']:
                cursor.execute(
                    """
                    INSERT INTO user_media (telegram_user_id, complaint_id, media_type, upload_method, 
                                          file_id, file_path, file_size, file_name, mime_type, caption, preserves_exif)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        telegram_user_id, complaint_id, media['type'], 
                        media.get('upload_method'), media['file_id'], media.get('file_path'), 
                        media.get('file_size'), media.get('file_name'), media.get('mime_type'),
                        media.get('caption'), media.get('preserves_exif', False)
                    )
                )
        
        conn.commit()
        return jsonify({
            "status": "success",
            "message": "Complaint successfully generated and submitted.",
            "complaint_id": complaint_id, "ghmc_id": ghmc_id,
            "data_saved": formal_report
        }), 201
    except sqlite3.Error as e:
        conn.rollback()
        return jsonify({"error": "Database error", "details": str(e)}), 500
    finally:
        conn.close()

# ==================== 7. GHMC ADMIN PORTAL API ENDPOINTS ====================
# (No changes in this section)
@app.route('/api/admin/complaints', methods=['GET'])
def get_all_complaints():
    query = "SELECT * FROM complaints WHERE 1=1"
    params = []
    if request.args.get('status'):
        query += " AND status = ?"
        params.append(request.args.get('status'))
    if request.args.get('category'):
        query += " AND category = ?"
        params.append(request.args.get('category'))
    if request.args.get('priority'):
        query += " AND priority = ?"
        params.append(request.args.get('priority'))
    if request.args.get('zone'):
        query += " AND zone LIKE ?"
        params.append(f"%{request.args.get('zone')}%")
    query += " ORDER BY created_at DESC"
    limit = int(request.args.get('limit', 50))
    offset = int(request.args.get('offset', 0))
    query += " LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    conn = get_db_connection()
    complaints = conn.execute(query, params).fetchall()
    conn.close()
    return jsonify([dict(row) for row in complaints])

@app.route('/api/admin/complaints/<int:complaint_id>', methods=['GET'])
def get_complaint_by_id(complaint_id):
    conn = get_db_connection()
    complaint = conn.execute('SELECT * FROM complaints WHERE id = ?', (complaint_id,)).fetchone()
    conn.close()
    if complaint is None:
        return jsonify({"error": "Complaint not found"}), 404
    return jsonify(dict(complaint))

@app.route('/api/admin/complaints/<int:complaint_id>/status', methods=['PUT'])
def update_complaint_status(complaint_id):
    data = request.get_json()
    new_status = data.get('status')
    if not new_status:
        return jsonify({"error": "'status' is required"}), 400
    conn = get_db_connection()
    try:
        old_complaint = conn.execute('SELECT status FROM complaints WHERE id = ?', (complaint_id,)).fetchone()
        if not old_complaint:
            return jsonify({"error": "Complaint not found"}), 404
        conn.execute('UPDATE complaints SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?', (new_status, complaint_id))
        conn.execute(
            'INSERT INTO status_history (complaint_id, old_status, new_status, changed_by, comments) VALUES (?, ?, ?, ?, ?)',
            (complaint_id, old_complaint['status'], new_status, data.get('changed_by', 'Admin'), data.get('comments', ''))
        )
        conn.commit()
        return jsonify({"status": "success", "message": f"Complaint {complaint_id} status updated to '{new_status}'"})
    except sqlite3.Error as e:
        conn.rollback()
        return jsonify({"error": "Database error", "details": str(e)}), 500
    finally:
        conn.close()

# ==================== NEW: 8. USER DATA MANAGEMENT ENDPOINTS ====================

@app.route('/api/users', methods=['POST'])
def save_telegram_user():
    """Save or update Telegram user data"""
    data = request.get_json()
    if not data or 'telegram_user_id' not in data:
        return jsonify({"error": "telegram_user_id is required"}), 400
    
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT OR REPLACE INTO telegram_users 
            (telegram_user_id, username, first_name, last_name, language_code, phone_number, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (
                data['telegram_user_id'],
                data.get('username'),
                data.get('first_name'),
                data.get('last_name'),
                data.get('language_code', 'en'),
                data.get('phone_number')
            )
        )
        conn.commit()
        return jsonify({"status": "success", "message": "User data saved"}), 201
    except sqlite3.Error as e:
        conn.rollback()
        return jsonify({"error": "Database error", "details": str(e)}), 500
    finally:
        conn.close()

@app.route('/api/users/<telegram_user_id>', methods=['GET'])
def get_telegram_user(telegram_user_id):
    """Get Telegram user data"""
    conn = get_db_connection()
    user = conn.execute(
        'SELECT * FROM telegram_users WHERE telegram_user_id = ?', 
        (telegram_user_id,)
    ).fetchone()
    conn.close()
    
    if user is None:
        return jsonify({"error": "User not found"}), 404
    return jsonify(dict(user))

@app.route('/api/users/<telegram_user_id>/media', methods=['POST'])
def save_user_media():
    """Save user media (images, audio files)"""
    data = request.get_json()
    if not data or 'telegram_user_id' not in data or 'media_type' not in data:
        return jsonify({"error": "telegram_user_id and media_type are required"}), 400
    
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO user_media 
            (telegram_user_id, complaint_id, media_type, upload_method, file_id, file_path, 
             file_size, file_name, mime_type, caption, preserves_exif)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data['telegram_user_id'],
                data.get('complaint_id'),
                data['media_type'],
                data.get('upload_method'),
                data['file_id'],
                data.get('file_path'),
                data.get('file_size'),
                data.get('file_name'),
                data.get('mime_type'),
                data.get('caption'),
                data.get('preserves_exif', False)
            )
        )
        media_id = cursor.lastrowid
        conn.commit()
        return jsonify({"status": "success", "media_id": media_id}), 201
    except sqlite3.Error as e:
        conn.rollback()
        return jsonify({"error": "Database error", "details": str(e)}), 500
    finally:
        conn.close()

@app.route('/api/users/<telegram_user_id>/complaints', methods=['GET'])
def get_user_complaints(telegram_user_id):
    """Get all complaints submitted by a user"""
    conn = get_db_connection()
    complaints = conn.execute(
        """
        SELECT c.*, u.username, u.first_name 
        FROM complaints c 
        LEFT JOIN telegram_users u ON c.submitted_by = u.telegram_user_id 
        WHERE c.submitted_by = ? 
        ORDER BY c.created_at DESC
        """, 
        (telegram_user_id,)
    ).fetchall()
    conn.close()
    return jsonify([dict(row) for row in complaints])

# ==================== NEW: 9. GEOLOCATION FALLBACK ENDPOINT ====================

@app.route('/request-location', methods=['GET'])
def request_location_page():
    """Serves a simple HTML page to get GPS coordinates from the user's browser."""
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Get My Location</title>
        <style>
            body { font-family: sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; flex-direction: column; background-color: #f4f4f9; }
            .container { text-align: center; padding: 2rem; background-color: white; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
            h1 { color: #333; }
            button { background-color: #007bff; color: white; border: none; padding: 12px 24px; font-size: 16px; border-radius: 5px; cursor: pointer; transition: background-color 0.3s; }
            button:hover { background-color: #0056b3; }
            #locationData { margin-top: 1.5rem; font-size: 1.1rem; color: #555; background-color: #e9ecef; padding: 10px; border-radius: 5px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Location Access</h1>
            <p>Please share your location to report the issue accurately.</p>
            <button onclick="getLocation()">Get Current Location</button>
            <p id="locationData">Your location will appear here...</p>
        </div>
        <script>
            function getLocation() {
                const locationPara = document.getElementById('locationData');
                if (navigator.geolocation) {
                    locationPara.textContent = "Requesting location...";
                    navigator.geolocation.getCurrentPosition(showPosition, showError);
                } else {
                    locationPara.textContent = "Geolocation is not supported by this browser.";
                }
            }

            function showPosition(position) {
                const lat = position.coords.latitude;
                const lon = position.coords.longitude;
                const locationPara = document.getElementById('locationData');
                locationPara.innerHTML = <b>Latitude:</b> ${lat.toFixed(6)} <br> <b>Longitude:</b> ${lon.toFixed(6)};
            }

            function showError(error) {
                const locationPara = document.getElementById('locationData');
                switch(error.code) {
                    case error.PERMISSION_DENIED:
                        locationPara.textContent = "User denied the request for Geolocation."
                        break;
                    case error.POSITION_UNAVAILABLE:
                        locationPara.textContent = "Location information is unavailable."
                        break;
                    case error.TIMEOUT:
                        locationPara.textContent = "The request to get user location timed out."
                        break;
                    case error.UNKNOWN_ERROR:
                        locationPara.textContent = "An unknown error occurred."
                        break;
                }
            }
        </script>
    </body>
    </html>
    """
    return render_template_string(html_content)


# ==================== 9. RUN FLASK APP ====================

if __name__ == '__main__':
    # Create /tmp directory if it doesn't exist for audio file handling
    if not os.path.exists('/tmp'):
        os.makedirs('/tmp')
    init_database()
    app.run(debug=True, port=5001)