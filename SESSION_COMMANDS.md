# FixMyHyd Bot - Text Commands Guide

## 🚀 **No Telegram Settings Required!**
Users can interact with the bot using simple text commands - no need to enable keyboards or change any Telegram settings.

## 📋 **Session Management Commands**

### **Starting a Report**
- `/report` - Start a new complaint report

### **When You Have an Active Session**
- **continue** - Resume working on your active session
- **new** - Cancel old session and start fresh  
- **cancel** - Cancel the active session

### **Adding Details to Your Report**
- **submit** - Submit your report to GHMC (when ready)
- **add** - Add more description to your report
- **status** - Check what's missing from your session
- **help** - Show available commands
- **cancel** - Cancel the current report

### **During Confirmation**
- **yes** / **confirm** - Submit the complaint to GHMC
- **no** / **cancel** - Cancel the submission
- **back** - Go back to add more details

## 🎯 **How It Works**

### 1. **Session Management**
```
User: /report
Bot: "You have an active session: [details]
      Type 'continue' to keep working or 'new' to start fresh"
User: continue
Bot: "Continuing session... Type 'submit' when ready"
```

### 2. **Adding Details**
```
User: submit
Bot: "Cannot submit yet! Missing: description
      Please add more information first"
User: The road has big potholes
Bot: "Description added! Type 'submit' when ready"
```

### 3. **Final Submission**
```
User: submit
Bot: "Complaint Summary: [details]
      Type 'yes' to confirm or 'no' to cancel"
User: yes
Bot: "✅ Complaint submitted! GHMC ID: 12345"
```

## ⚡ **Key Benefits**

✅ **No Keyboard Setup** - Works with any Telegram client
✅ **Simple Commands** - Easy to remember text commands  
✅ **Flexible Input** - Multiple ways to say the same thing
✅ **Clear Guidance** - Bot always tells users what to do next
✅ **Session Persistence** - Can resume interrupted sessions
✅ **Command Help** - Type 'help' anytime for guidance

## 🔧 **For Developers**

All session management is handled in:
- `report_handler_simple.py` - Main simplified handler
- `report_handler_modules.py` - Modular components
- `session_manager.py` - Session persistence

No additional Telegram bot settings required - everything works through text messages!