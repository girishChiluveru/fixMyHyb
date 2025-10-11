"""All bot messages in one place for easy management and multi-language support"""

class Messages:
    """English messages"""
    
    # Welcome messages
    WELCOME_NEW_USER = """
🙏 Namaste, {first_name}! Welcome to FixMyHyd!

Your smart assistant for reporting civic issues in Hyderabad 🏙️

*HOW IT WORKS:*
1️⃣ Click /report or send a photo
2️⃣ We extract location & categorize automatically
3️⃣ Complaint submitted to GHMC instantly
4️⃣ Get real-time status updates

🎯 Zero forms, zero hassle!

Choose your language to continue:
"""
    
    WELCOME_BACK = """
Welcome back, {first_name}! 👋

Ready to make Hyderabad better?

*Quick Actions:*
📸 /report - Report an issue
📊 /status - Check your complaints  
❓ /help - Need assistance?

Just send a photo to get started! 🚀
"""
    
    # Report flow messages
    REPORT_START = """
📸 *Report a Civic Issue*

Please send a PHOTO of the problem.

*Make sure your photo:*
✅ Shows the issue clearly
✅ Has location enabled (GPS)
✅ Is well-lit and focused

*Optional:* Add a voice note or text description for more details.

Type /cancel to stop reporting.
"""
    
    PROCESSING_IMAGE = "📥 Processing your image... Please wait."
    
    GPS_FOUND = """
✅ *Location Detected!*

📍 Latitude: {lat:.6f}
📍 Longitude: {lon:.6f}
🗺️ [View on Google Maps]({maps_url})

Now analyzing the issue type...
"""
    
    GPS_NOT_FOUND = """
⚠️ *No Location Data Found*

Your image doesn't have GPS coordinates.

*Please choose an option:*
1️⃣ Share your live location
2️⃣ Take a new photo with location enabled
3️⃣ Cancel and try again later
"""
    
    IMAGE_REQUIRED = """
⚠️ *Photo Required*

To report a civic issue, you must send a PHOTO.

*Why we need a photo:*
✅ Verifies the actual problem
✅ Helps extract GPS location
✅ Speeds up GHMC processing

Please send a photo to continue, or /cancel to stop.
"""
    
    COMPLAINT_SUMMARY = """
📋 *Complaint Summary*

*Issue Type:* {category}
*Description:* {description}
*Location:* {address}
*Confidence:* {confidence}%

*Is this correct?*
Reply *Yes* to submit or *No* to cancel.
"""
    
    COMPLAINT_SUBMITTED = """
✅ *Complaint Submitted Successfully!*

*Complaint ID:* #{complaint_id}
*Category:* {category}
*Submitted:* {timestamp}

We'll notify you once GHMC updates the status.

Use /status to check your complaints anytime.
"""
    
    REPORT_CANCELLED = """
❌ Reporting cancelled.

Use /report to start a new report anytime!
"""
    
    # Help message
    HELP_MESSAGE = """
❓ *How to Use FixMyHyd*

*REPORTING AN ISSUE:*
1. Type /report or send a photo directly
2. Make sure location is enabled on your phone
3. Add voice/text description (optional)
4. Confirm and submit!

*CHECKING STATUS:*
Type /status to see all your complaints

*TIPS FOR BEST RESULTS:*
📸 Take clear, well-lit photos
📍 Enable GPS before taking photo
🎤 Add voice notes in Telugu/Hindi/English
🔄 One issue per report

*SUPPORTED CATEGORIES:*
- Garbage & Sanitation
- Potholes & Roads
- Street Lights
- Water Supply
- Drainage Issues
- Parks & Gardens

*LANGUAGES:*
English, తెలుగు, हिंदी

*NEED HELP?*
Contact: support@fixmyhyd.com
"""
    
    # Status messages
    NO_COMPLAINTS = """
📊 *Your Complaints*

You haven't submitted any complaints yet.

Use /report to report your first civic issue! 📸
"""
    
    # Error messages
    ERROR_GENERIC = """
❌ Oops! Something went wrong.

Please try again or contact support if the issue persists.
"""
    
    ERROR_INVALID_IMAGE = """
⚠️ Invalid image file.

Please send a valid JPG/PNG image and try again.
"""


class TeluguMessages:
    """Telugu messages"""
    
    WELCOME_NEW_USER = """
🙏 నమస్కారం, {first_name}! FixMyHyd కు స్వాగతం!

హైదరాబాద్ లో పౌర సమస్యలను నివేదించే మీ స్మార్ట్ సహాయకుడు 🏙️

*ఎలా పని చేస్తుంది:*
1️⃣ /report క్లిక్ చేయండి లేదా ఫోటో పంపండి
2️⃣ మేము స్థానం మరియు వర్గీకరణను స్వయంచాలకంగా సేకరిస్తాము
3️⃣ ఫిర్యాదు తక్షణమే GHMC కు సమర్పించబడుతుంది
4️⃣ రియల్-టైమ్ స్థితి నవీకరణలు పొందండి

🎯 ఫారాలు లేవు, ఇబ్బందులు లేవు!

కొనసాగించడానికి మీ భాషను ఎంచుకోండి:
"""
    
    REPORT_START = """
📸 *పౌర సమస్యను నివేదించండి*

దయచేసి సమస్య యొక్క ఫోటోను పంపండి.

*మీ ఫోటో ఇలా ఉండాలి:*
✅ సమస్యను స్పష్టంగా చూపించాలి
✅ లొకేషన్ ఎనేబుల్ చేయాలి (GPS)
✅ వెలుతురుగా మరియు ఫోకస్ లో ఉండాలి

*ఐచ్ఛికం:* మరిన్ని వివరాల కోసం వాయిస్ నోట్ లేదా టెక్స్ట్ జోడించండి.

నివేదికను ఆపడానికి /cancel టైప్ చేయండి.
"""


class HindiMessages:
    """Hindi messages"""
    
    WELCOME_NEW_USER = """
🙏 नमस्ते, {first_name}! FixMyHyd में आपका स्वागत है!

हैदराबाद में नागरिक समस्याओं की रिपोर्ट करने के लिए आपका स्मार्ट सहायक 🏙️

*यह कैसे काम करता है:*
1️⃣ /report पर क्लिक करें या फोटो भेजें
2️⃣ हम स्वचालित रूप से स्थान और श्रेणी निकालते हैं
3️⃣ शिकायत तुरंत GHMC को सबमिट की जाती है
4️⃣ रियल-टाइम स्टेटस अपडेट प्राप्त करें

🎯 कोई फॉर्म नहीं, कोई परेशानी नहीं!

जारी रखने के लिए अपनी भाषा चुनें:
"""
    
    REPORT_START = """
📸 *नागरिक समस्या की रिपोर्ट करें*

कृपया समस्या की फोटो भेजें।

*सुनिश्चित करें कि आपकी फोटो:*
✅ समस्या को स्पष्ट रूप से दिखाती है
✅ लोकेशन सक्षम है (GPS)
✅ अच्छी तरह से रोशन और फोकस में है

*वैकल्पिक:* अधिक विवरण के लिए वॉइस नोट या टेक्स्ट जोड़ें।

रिपोर्टिंग रोकने के लिए /cancel टाइप करें।
"""


def get_messages(language='en'):
    """Get messages for specified language"""
    if language == 'te':
        return TeluguMessages()
    elif language == 'hi':
        return HindiMessages()
    else:
        return Messages()