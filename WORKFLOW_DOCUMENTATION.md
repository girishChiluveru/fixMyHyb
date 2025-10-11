t# FixMyHyd Bot - Complete Workflow and Architecture

## Overview
FixMyHyd is a Telegram bot that allows citizens to report civic issues in Hyderabad. The bot integrates with a Flask backend for AI-powered analysis and GHMC complaint management.

## System Architecture

```
[Telegram User] → [Telegram Bot] → [Flask API Backend] → [SQLite Database]
                                      ↓
                              [Google Gemini AI] → [GPS Extraction] → [GHMC Portal]
```

## Database Schema

### Tables Created:

1. **complaints** - Stores all complaint data
   - id, ghmc_id, category, priority, subject, description
   - location, zone, gps_lat, gps_lng, status
   - submitted_by (links to telegram_user_id), created_at, updated_at

2. **status_history** - Tracks complaint status changes
   - complaint_id, old_status, new_status, changed_by, comments, created_at

3. **telegram_users** (NEW) - Stores user data
   - telegram_user_id, username, first_name, last_name
   - language_code, phone_number, created_at, updated_at

4. **user_media** (NEW) - Stores media files (images, voice notes)
   - telegram_user_id, complaint_id, media_type, file_id
   - file_path, file_size, caption, created_at

## Bot Workflow

### 1. User Registration/Data Storage
When a user interacts with the bot:
- User data is automatically saved to `telegram_users` table
- Information includes: user_id, username, first_name, last_name, language

### 2. Complaint Reporting Process

#### Step 1: Photo Submission (MANDATORY)
```
User sends photo → Bot downloads image → GPS extraction → AI analysis
```
- **GPS Extraction**: Now implemented with debug logging
  - Extracts EXIF GPS data from images
  - Converts DMS to decimal degrees
  - Stores coordinates and generates Google Maps link
  - Debug logs show extraction process details

- **AI Image Analysis**: 
  - Sends image to Flask backend
  - Gemini AI analyzes and categorizes the issue
  - Returns category and summary

- **Media Storage**:
  - Image file stored in temp directory
  - Image metadata saved to `user_media` table
  - Links file_id, file_path, file_size to user and complaint

#### Step 2: Voice/Text Input (At least one required)
```
User provides description via voice OR text → AI processing → Categorization
```

**Voice Note Processing**:
- Downloads voice file (.ogg format)
- Sends to Gemini AI for transcription
- Stores transcription and voice metadata
- Voice file metadata saved to `user_media` table

**Text Description Processing**:
- Sends text to Gemini AI for analysis
- AI categorizes issue and determines priority
- Extracts actionable steps for municipal team

#### Step 3: Confirmation & Submission
```
Show summary → User confirms → Submit to backend → Generate GHMC ID
```
- Displays complete analysis and GPS data
- User confirms submission
- Creates formal report using AI
- Stores in database with user tracking
- Returns GHMC complaint ID

## Debug Features Added

### GPS Extraction Debug Logs:
```
[GPS_DEBUG] Starting GPS extraction for: /path/to/image.jpg
[GPS_DEBUG] File exists: True
[GPS_DEBUG] File size: 2048576
[GPS_DEBUG] Image format: JPEG
[GPS_DEBUG] Image size: (1920, 1080)
[GPS_DEBUG] Has EXIF data: True
[GPS_DEBUG] Found GPS Info: {...}
[GPS_DEBUG] GPS GPSLatitude: (17, 23, 45.6)
[GPS_DEBUG] Converted latitude: 17.396
[GPS_DEBUG] Successfully extracted GPS: 17.396, 78.486
```

### Media Processing Debug Logs:
```
[MEDIA_DEBUG] Photo file_id: AgACAgIAAxkBAAIC...
[MEDIA_DEBUG] Photo file_size: 2048576
[MEDIA_DEBUG] Photo caption: Road damage near KBR Park
[MEDIA_DEBUG] Voice file_id: AwACAgIAAxkBAAIC...
[MEDIA_DEBUG] Voice file_size: 524288
[MEDIA_DEBUG] Voice duration: 15
```

## API Endpoints

### New User Management Endpoints:
- `POST /api/users` - Save/update user data
- `GET /api/users/{telegram_user_id}` - Get user data
- `POST /api/users/{telegram_user_id}/media` - Save media files
- `GET /api/users/{telegram_user_id}/complaints` - Get user's complaints

### Existing Complaint Endpoints:
- `POST /api/analyze-image` - AI image analysis
- `POST /api/transcribe-voice` - Voice transcription
- `POST /api/analyze-text` - Text analysis
- `POST /api/generate-report` - Submit complaint
- `GET /api/admin/complaints` - List all complaints
- `PUT /api/admin/complaints/{id}/status` - Update status

## File Structure
```
fixmyhyd-bot/
├── app.py                 # Flask backend (main API)
├── run.py                 # Telegram bot entry point
├── bot/
│   ├── main.py           # Bot initialization
│   ├── handlers/         # Message handlers
│   │   ├── report_handler.py    # Complaint reporting (UPDATED)
│   │   ├── start_handler.py     # Start/welcome
│   │   ├── status_handler.py    # Status checking
│   │   └── help_handler.py      # Help system
│   ├── services/
│   │   └── api_client.py        # API communication (UPDATED)
│   └── utils/
│       ├── gps_extractor.py     # GPS extraction (IMPLEMENTED)
│       └── messages.py          # Bot messages
├── config/
│   └── settings.py       # Configuration
├── fixmyhyd.db          # SQLite database (UPDATED SCHEMA)
└── temp/                # Temporary media files
```

## Key Improvements Made

1. **GPS Extraction**: 
   - Fully implemented EXIF GPS data extraction
   - Added comprehensive debug logging
   - Handles DMS to decimal degree conversion
   - Error handling for images without GPS

2. **User Data Storage**:
   - All user interactions tracked in database
   - Media files linked to users and complaints
   - Historical data maintained

3. **Enhanced Debugging**:
   - Detailed logging for GPS extraction process
   - Media file processing logs
   - API call debugging

4. **Database Improvements**:
   - New tables for users and media
   - Foreign key relationships
   - Proper data normalization

## Testing the Bot

### Requirements:
1. Set GOOGLE_API_KEY in .env file
2. Set TELEGRAM_BOT_TOKEN in .env file
3. Ensure Flask backend is running on port 5001

### Test Flow:
1. Send `/start` to bot
2. Send `/report` to start complaint
3. Send a photo with GPS EXIF data
4. Send voice note or type description
5. Confirm submission
6. Check database for stored data

### Debug Commands:
- Check logs for GPS extraction details
- Verify media files are stored in `user_media` table
- Check `telegram_users` table for user data
- Monitor API calls in Flask logs

## Error Handling

The system now includes proper error handling for:
- Images without GPS data
- Failed AI API calls  
- Database connection issues
- File download/upload failures
- Invalid user input

## Future Enhancements

1. **Admin Dashboard**: Web interface for GHMC officials
2. **Real-time Updates**: WebSocket notifications for status changes
3. **Location Services**: Fallback GPS via Telegram location sharing
4. **Media Compression**: Optimize file storage
5. **Analytics**: Usage statistics and reporting trends