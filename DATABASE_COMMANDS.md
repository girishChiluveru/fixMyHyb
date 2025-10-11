# SQLite Database Commands for FixMyHyd Bot

## Database Schema Overview

The FixMyHyd bot uses 4 main tables:
1. **complaints** - Main complaint data
2. **status_history** - Tracks complaint status changes
3. **telegram_users** - User profile information
4. **user_media** - Media files (images, voice notes)

---

## 📋 BASIC DATABASE OPERATIONS

### Connect to Database
```bash
sqlite3 fixmyhyd.db
```

### List All Tables
```sql
.tables
```

### Show Table Schema
```sql
.schema
.schema complaints
.schema telegram_users
.schema user_media
.schema status_history
```

### Exit SQLite
```sql
.exit
```

---

## 👤 USER MANAGEMENT

### View All Users
```sql
SELECT * FROM telegram_users;
```

### View User Details by ID
```sql
SELECT * FROM telegram_users WHERE telegram_user_id = 'USER_ID_HERE';
```

### Count Total Users
```sql
SELECT COUNT(*) as total_users FROM telegram_users;
```

### View Recent Users (Last 7 days)
```sql
SELECT telegram_user_id, username, first_name, created_at 
FROM telegram_users 
WHERE datetime(created_at) > datetime('now', '-7 days')
ORDER BY created_at DESC;
```

### Find Users by Name
```sql
SELECT * FROM telegram_users 
WHERE first_name LIKE '%NAME%' OR username LIKE '%NAME%';
```

### Update User Phone Number
```sql
UPDATE telegram_users 
SET phone_number = '+91XXXXXXXXXX', updated_at = CURRENT_TIMESTAMP 
WHERE telegram_user_id = 'USER_ID_HERE';
```

---

## 📋 COMPLAINT MANAGEMENT

### View All Complaints
```sql
SELECT * FROM complaints ORDER BY created_at DESC;
```

### View Recent Complaints (Last 24 hours)
```sql
SELECT ghmc_id, category, subject, status, created_at 
FROM complaints 
WHERE datetime(created_at) > datetime('now', '-1 day')
ORDER BY created_at DESC;
```

### Count Complaints by Category
```sql
SELECT category, COUNT(*) as count 
FROM complaints 
GROUP BY category 
ORDER BY count DESC;
```

### Count Complaints by Status
```sql
SELECT status, COUNT(*) as count 
FROM complaints 
GROUP BY status 
ORDER BY count DESC;
```

### View High Priority Complaints
```sql
SELECT ghmc_id, category, priority, subject, status, created_at 
FROM complaints 
WHERE priority = 'High' 
ORDER BY created_at DESC;
```

### View Complaints with GPS Data
```sql
SELECT ghmc_id, category, gps_lat, gps_lng, zone, created_at 
FROM complaints 
WHERE gps_lat IS NOT NULL AND gps_lng IS NOT NULL
ORDER BY created_at DESC;
```

### View Complaints by Zone
```sql
SELECT * FROM complaints 
WHERE zone LIKE '%Banjara Hills%' 
ORDER BY created_at DESC;
```

### Update Complaint Status
```sql
UPDATE complaints 
SET status = 'In Progress', updated_at = CURRENT_TIMESTAMP 
WHERE ghmc_id = 'GHMC_ID_HERE';
```

### View User's Complaint History
```sql
SELECT c.ghmc_id, c.category, c.status, c.created_at, u.username 
FROM complaints c 
JOIN telegram_users u ON c.submitted_by = u.telegram_user_id 
WHERE u.telegram_user_id = 'USER_ID_HERE'
ORDER BY c.created_at DESC;
```

---

## 📱 MEDIA FILE MANAGEMENT

### View All Media Files
```sql
SELECT * FROM user_media ORDER BY created_at DESC;
```

### View Images Only
```sql
SELECT * FROM user_media 
WHERE media_type = 'image' 
ORDER BY created_at DESC;
```

### View Voice Notes Only
```sql
SELECT * FROM user_media 
WHERE media_type = 'voice' 
ORDER BY created_at DESC;
```

### View Media Files with Complaints
```sql
SELECT m.media_type, m.file_size, m.caption, c.ghmc_id, c.category 
FROM user_media m 
JOIN complaints c ON m.complaint_id = c.id 
ORDER BY m.created_at DESC;
```

### View Files by User
```sql
SELECT m.*, u.username 
FROM user_media m 
JOIN telegram_users u ON m.telegram_user_id = u.telegram_user_id 
WHERE u.telegram_user_id = 'USER_ID_HERE'
ORDER BY m.created_at DESC;
```

### Check Storage Usage
```sql
SELECT 
    media_type,
    COUNT(*) as file_count,
    SUM(file_size) as total_size_bytes,
    ROUND(SUM(file_size) / 1024.0 / 1024.0, 2) as total_size_mb
FROM user_media 
GROUP BY media_type;
```

### Clean Up Old Media Files (Query Only - Don't Delete)
```sql
-- Find files older than 30 days
SELECT file_path, file_size, created_at 
FROM user_media 
WHERE datetime(created_at) < datetime('now', '-30 days');
```

---

## 📊 ANALYTICS & REPORTING

### Daily Complaint Report
```sql
SELECT 
    DATE(created_at) as complaint_date,
    COUNT(*) as complaints_count,
    COUNT(CASE WHEN gps_lat IS NOT NULL THEN 1 END) as with_gps
FROM complaints 
WHERE datetime(created_at) > datetime('now', '-30 days')
GROUP BY DATE(created_at)
ORDER BY complaint_date DESC;
```

### Category Analysis
```sql
SELECT 
    category,
    COUNT(*) as total,
    COUNT(CASE WHEN status = 'Submitted' THEN 1 END) as pending,
    COUNT(CASE WHEN status = 'In Progress' THEN 1 END) as in_progress,
    COUNT(CASE WHEN status = 'Resolved' THEN 1 END) as resolved
FROM complaints 
GROUP BY category
ORDER BY total DESC;
```

### User Activity Report
```sql
SELECT 
    u.username,
    u.first_name,
    COUNT(c.id) as complaints_submitted,
    MAX(c.created_at) as last_complaint
FROM telegram_users u 
LEFT JOIN complaints c ON u.telegram_user_id = c.submitted_by 
GROUP BY u.telegram_user_id 
HAVING complaints_submitted > 0
ORDER BY complaints_submitted DESC;
```

### GPS Data Coverage
```sql
SELECT 
    COUNT(*) as total_complaints,
    COUNT(CASE WHEN gps_lat IS NOT NULL THEN 1 END) as with_gps,
    ROUND(
        COUNT(CASE WHEN gps_lat IS NOT NULL THEN 1 END) * 100.0 / COUNT(*), 2
    ) as gps_coverage_percentage
FROM complaints;
```

---

## 🔧 MAINTENANCE COMMANDS

### Database Integrity Check
```sql
PRAGMA integrity_check;
```

### Database Size
```sql
.databases
```

### Vacuum Database (Optimize)
```sql
VACUUM;
```

### Backup Database
```bash
# Run from command line, not in SQLite
sqlite3 fixmyhyd.db ".backup backup_$(date +%Y%m%d).db"
```

### Export Data to CSV
```sql
.mode csv
.headers on
.output complaints_export.csv
SELECT * FROM complaints;
.output stdout
```

---

## 🚨 EMERGENCY QUERIES

### Find Stuck Complaints (No Updates for 7+ Days)
```sql
SELECT ghmc_id, category, status, created_at, updated_at 
FROM complaints 
WHERE status IN ('Submitted', 'In Progress') 
AND datetime(updated_at) < datetime('now', '-7 days')
ORDER BY created_at ASC;
```

### Find Complaints Without Media
```sql
SELECT c.ghmc_id, c.category, c.created_at 
FROM complaints c 
LEFT JOIN user_media m ON c.id = m.complaint_id 
WHERE m.id IS NULL
ORDER BY c.created_at DESC;
```

### Find Large Media Files (>5MB)
```sql
SELECT file_path, file_size, media_type, created_at 
FROM user_media 
WHERE file_size > 5242880 
ORDER BY file_size DESC;
```

---

## 📝 COMMON MAINTENANCE TASKS

### Weekly Cleanup Script
```sql
-- 1. Check database integrity
PRAGMA integrity_check;

-- 2. Update complaint counts
SELECT 
    'Total Complaints: ' || COUNT(*) as stats FROM complaints
UNION ALL
SELECT 
    'Active Users: ' || COUNT(*) FROM telegram_users
UNION ALL
SELECT 
    'Media Files: ' || COUNT(*) FROM user_media;

-- 3. Identify issues
SELECT 'Complaints without GPS: ' || COUNT(*) 
FROM complaints WHERE gps_lat IS NULL;
```

### Performance Optimization
```sql
-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_complaints_status ON complaints(status);
CREATE INDEX IF NOT EXISTS idx_complaints_category ON complaints(category);
CREATE INDEX IF NOT EXISTS idx_complaints_created ON complaints(created_at);
CREATE INDEX IF NOT EXISTS idx_media_user ON user_media(telegram_user_id);
CREATE INDEX IF NOT EXISTS idx_media_complaint ON user_media(complaint_id);
```

---

## 💡 TIPS

1. **Regular Backups**: Run backup command daily
2. **Monitor Storage**: Check media file sizes regularly
3. **Index Usage**: Use indexes for frequently queried columns
4. **Data Cleanup**: Remove old temporary files periodically
5. **Performance**: Use LIMIT clause for large result sets

## 🔍 Example Data Queries

### Get Complete Complaint Details
```sql
SELECT 
    c.ghmc_id,
    c.category,
    c.subject,
    c.status,
    c.gps_lat,
    c.gps_lng,
    u.username,
    u.first_name,
    COUNT(m.id) as media_count,
    c.created_at
FROM complaints c
LEFT JOIN telegram_users u ON c.submitted_by = u.telegram_user_id
LEFT JOIN user_media m ON c.id = m.complaint_id
GROUP BY c.id
ORDER BY c.created_at DESC
LIMIT 10;
```