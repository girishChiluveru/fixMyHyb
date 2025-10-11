# FixMyHyd Bot Testing Guide

## 🔧 **SOLUTION IMPLEMENTED**

### ✅ **Problem Solved**: Telegram EXIF Data Stripping
- **Issue**: Telegram removes GPS metadata from regular photo uploads
- **Solution**: Support both photo and document uploads
- **Fallback**: Manual location sharing when GPS unavailable

---

## 🖥️ **DEBUG CONSOLE SYSTEM**

### **Clean Console Output**
The bot now features a clean debug system that replaces verbose HTTP logs with meaningful messages:

**Debug Messages Include:**
- 🆕 New user joins
- 💾 User data saved to database
- 📁 File uploads with type information
- 🤖 AI analysis progress
- 📍 GPS extraction results
- 🎤 Voice transcription progress
- 📤 Report submissions

**Configuration:**
```bash
# In .env file
DEBUG_CONSOLE=true   # Show debug messages (default)
DEBUG_CONSOLE=false  # Hide debug messages
```

**Example Clean Output:**
```
🚀 Starting FixMyHyd Bot...
🌍 Environment: development
📍 GPS Extraction: Enabled
🤖 AI Analysis: Enabled
🎯 Debug Console: Enabled
==================================================
✅ Bot is running! Press Ctrl+C to stop.

🆕 New user joined: @john_doe (ID: 123456789)
💾 User saved to database: @john_doe
📁 File uploaded: IMG_20241011_142030.jpg (Type: document)
🤖 AI analysis started for: IMG_20241011_142030.jpg
📍 GPS extracted from IMG_20241011_142030.jpg: 17.385044, 78.486671
✅ AI analysis completed: Road Maintenance - IMG_20241011_142030.jpg
📤 Report submitted: GHMC2024001234 (Category: Road Maintenance)
```

---

## 🧪 **TESTING CHECKLIST**

### **Prerequisites**
- [ ] Flask API running on `http://localhost:5001`
- [ ] Telegram bot token configured
- [ ] Google Gemini API key set up
- [ ] Database schema updated with new fields

### **Test 1: Photo Upload (Standard Method)**
**Steps:**
1. Send `/start` to bot
2. Send `/report` 
3. Send a regular photo (camera roll → send as photo)

**Expected Results:**
```
[UPLOAD_DEBUG] Image received as PHOTO - EXIF data likely stripped ⚠️
✅ Photo processed successfully!
⚠️ No GPS data found
Reason: No EXIF data found in image
💡 Try sending as Document next time
```

**Database Check:**
```sql
SELECT upload_method, preserves_exif, file_size 
FROM user_media 
WHERE media_type = 'image' 
ORDER BY created_at DESC LIMIT 1;
-- Expected: upload_method='photo', preserves_exif=0
```

### **Test 2: Document Upload (EXIF Preserved Method)**
**Steps:**
1. Send `/report` to bot
2. Tap attachment button (📎)
3. Select "Document" 
4. Choose "Gallery" or "File Manager"
5. Select an image file
6. Send as document

**Expected Results:**
```
[UPLOAD_DEBUG] Image received as DOCUMENT - EXIF data preserved ✅
✅ Document processed successfully!
📍 GPS Location Found:
Lat: 17.396000
Lon: 78.486000
📍 View on Map
```

**Database Check:**
```sql
SELECT upload_method, preserves_exif, file_name, mime_type 
FROM user_media 
WHERE media_type = 'image' 
ORDER BY created_at DESC LIMIT 1;
-- Expected: upload_method='document', preserves_exif=1, file_name='IMG_123.jpg'
```

### **Test 3: Manual Location Sharing**
**Steps:**
1. Send any image without GPS data
2. When prompted, tap "📍 Share My Current Location"
3. Allow location access

**Expected Results:**
```
[GPS_DEBUG] Location shared by user: 17.396000, 78.486000
✅ Location Received!
📍 Lat: 17.396000, Lon: 78.486000
📍 View on Map
```

**Database Check:**
```sql
SELECT gps_lat, gps_lng, has_gps 
FROM complaints 
ORDER BY created_at DESC LIMIT 1;
-- Expected: gps_lat=17.396, gps_lng=78.486
```

---

## 📱 **USER INSTRUCTIONS TO TEST**

### **Method 1: Regular Photo (Quick but no GPS)**
1. Open Telegram → FixMyHyd Bot
2. Send `/report`
3. Take or select photo normally
4. Send photo
5. When asked, share location manually

### **Method 2: Document Upload (Preserves GPS)**
1. Open Telegram → FixMyHyd Bot  
2. Send `/report`
3. **Tap 📎 (attachment) button**
4. **Select "Document"** (NOT Gallery)
5. **Choose "Gallery" from document options**
6. Select your image
7. **Send as document**

### **Visual Guide:**
```
❌ Wrong: Gallery → Photo → Send
✅ Correct: 📎 → Document → Gallery → Photo → Send
```

---

## 🗄️ **DATABASE VERIFICATION COMMANDS**

### **Check Upload Statistics**
```sql
SELECT 
    upload_method,
    COUNT(*) as uploads,
    SUM(CASE WHEN preserves_exif = 1 THEN 1 ELSE 0 END) as with_exif,
    ROUND(AVG(file_size)/1024.0, 2) as avg_size_kb
FROM user_media 
WHERE media_type = 'image'
GROUP BY upload_method;
```

### **GPS Coverage Analysis**
```sql
SELECT 
    COUNT(*) as total_complaints,
    COUNT(CASE WHEN gps_lat IS NOT NULL THEN 1 END) as with_gps,
    ROUND(COUNT(CASE WHEN gps_lat IS NOT NULL THEN 1 END) * 100.0 / COUNT(*), 1) as gps_percentage
FROM complaints;
```

### **Recent Uploads with Details**
```sql
SELECT 
    m.upload_method,
    m.preserves_exif,
    m.file_size,
    c.gps_lat IS NOT NULL as has_coordinates,
    m.created_at
FROM user_media m
LEFT JOIN complaints c ON m.complaint_id = c.id
WHERE m.media_type = 'image'
ORDER BY m.created_at DESC
LIMIT 10;
```

---

## 🔍 **TROUBLESHOOTING**

### **Problem: Bot doesn't recognize document**
**Solution:** 
- File must be an image (jpg, png, gif)
- Check MIME type in logs
- Try different image format

### **Problem: No GPS even from document**
**Possible Causes:**
- Image was taken without GPS enabled
- Photo edited/processed (strips EXIF)
- Camera app doesn't save GPS
- Indoor location with no GPS signal

**Debug Steps:**
1. Check logs for `[GPS_DEBUG]` messages
2. Verify EXIF data exists: `exif image.jpg` (command line)
3. Test with known GPS-enabled image

### **Problem: Database errors**
**Check:**
```sql
PRAGMA integrity_check;
.schema user_media
```

---

## 🎯 **SUCCESS CRITERIA**

### **Functional Requirements:**
- [ ] Bot accepts both photos and documents
- [ ] Document uploads preserve EXIF data
- [ ] Manual location sharing works as fallback
- [ ] All upload metadata stored in database
- [ ] GPS coordinates linked to complaints

### **User Experience:**
- [ ] Clear instructions on upload methods
- [ ] Helpful error messages
- [ ] Visual feedback on GPS status
- [ ] Smooth fallback to manual location

### **Technical:**
- [ ] Debug logging shows upload method
- [ ] Database stores all metadata fields
- [ ] API handles both upload types
- [ ] No crashes or data loss

---

## 📊 **PERFORMANCE MONITORING**

### **Daily Health Check**
```sql
-- Upload method distribution (last 24 hours)
SELECT 
    upload_method,
    COUNT(*) as count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 1) as percentage
FROM user_media 
WHERE datetime(created_at) > datetime('now', '-1 day')
AND media_type = 'image'
GROUP BY upload_method;

-- GPS success rate
SELECT 
    ROUND(
        COUNT(CASE WHEN gps_lat IS NOT NULL THEN 1 END) * 100.0 / COUNT(*), 1
    ) as gps_success_rate
FROM complaints 
WHERE datetime(created_at) > datetime('now', '-1 day');
```

### **Storage Analysis**
```sql
-- File size analysis by upload method
SELECT 
    upload_method,
    COUNT(*) as files,
    ROUND(SUM(file_size) / 1024.0 / 1024.0, 2) as total_mb,
    ROUND(AVG(file_size) / 1024.0, 2) as avg_kb
FROM user_media 
WHERE media_type = 'image'
GROUP BY upload_method;
```

---

## 🚀 **DEPLOYMENT CHECKLIST**

- [ ] Flask API running and responding
- [ ] Database schema updated with new columns
- [ ] Telegram bot handlers updated
- [ ] User instructions documented
- [ ] Monitoring queries ready
- [ ] Backup procedure tested
- [ ] Error handling verified

## 📞 **Support Commands**

### **For Users Having Issues:**
```sql
-- Find users struggling with uploads
SELECT DISTINCT u.username, u.first_name, COUNT(m.id) as uploads
FROM telegram_users u
JOIN user_media m ON u.telegram_user_id = m.telegram_user_id
WHERE m.preserves_exif = 0
GROUP BY u.telegram_user_id
HAVING uploads > 1;
```

### **Success Stories:**
```sql
-- Users successfully using document uploads
SELECT u.username, COUNT(*) as successful_uploads
FROM telegram_users u
JOIN user_media m ON u.telegram_user_id = m.telegram_user_id
WHERE m.preserves_exif = 1
GROUP BY u.telegram_user_id
ORDER BY successful_uploads DESC;
```

**The bot now handles both photo and document uploads, preserves EXIF data when possible, and provides manual location sharing as a reliable fallback. All upload methods and metadata are tracked in the database for analytics and support purposes.**