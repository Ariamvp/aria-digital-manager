import os
import requests
from supabase import create_client, Client
from dotenv import load_dotenv
from cryptography.fernet import Fernet

load_dotenv()

# ==========================================
# SUPABASE CONFIG
# ==========================================
# Match these to your exact Railway variable names
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_ANON_KEY") 
supabase: Client = create_client(url, key)

# Admin client (for bypassing RLS)
admin_key = os.getenv("SUPABASE_SERVICE_KEY") 
supabase_admin: Client = create_client(url, admin_key)

# ==========================================
# ENCRYPTION CONFIG
# ==========================================
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")
if not ENCRYPTION_KEY:
    raise ValueError("ENCRYPTION_KEY is missing from your environment variables!")

fernet = Fernet(ENCRYPTION_KEY)

def encrypt_text(plain_text: str) -> str:
    if not plain_text: return ""
    return fernet.encrypt(plain_text.encode()).decode()

def decrypt_text(encrypted_text: str) -> str:
    if not encrypted_text: return ""
    try:
        return fernet.decrypt(encrypted_text.encode()).decode()
    except Exception:
        # Fallback: If it fails, it was saved as plain text before encryption
        return encrypted_text 

# ==========================================
# USER SETTINGS FUNCTIONS
# ==========================================
def get_user_settings(user_id: str):
    try:
        res = supabase_admin.table("business_settings").select("*").eq("user_id", user_id).execute()
        if res.data:
            user_data = res.data[0]
            # Decrypt sensitive fields
            sensitive_fields = ['gmail_app_password', 'telegram_bot_token', 'telegram_chat_id']
            for field in sensitive_fields:
                if field in user_data and user_data[field]:
                    user_data[field] = decrypt_text(user_data[field])
            return user_data
        return None
    except Exception as e:
        print(f"Error getting settings: {e}")
        return None

def save_user_settings(user_id: str, settings_data: dict):
    try:
        # 1. Encrypt sensitive fields
        sensitive_fields = ['gmail_app_password', 'telegram_bot_token', 'telegram_chat_id']
        for field in sensitive_fields:
            if field in settings_data and settings_data[field]:
                settings_data[field] = encrypt_text(settings_data[field])
        
        # 2. First, delete any existing record for this user
        supabase_admin.table("business_settings").delete().eq("user_id", user_id).execute()
        
        # 3. Then insert a fresh record
        res = supabase_admin.table("business_settings").insert(
            {"user_id": user_id, **settings_data}
        ).execute()
        
        if res.data:
            print(f"✅ Settings saved successfully for user {user_id}")
            return res.data
        else:
            print(f"❌ Failed to save settings - no data returned")
            return None
            
    except Exception as e:
        print(f"❌ Error saving settings: {str(e)}")
        return None

def save_approval(user_id: str, approval_data: dict):
    try:
        res = supabase_admin.table("lead_approvals").insert(
            {"user_id": user_id, **approval_data}
        ).execute()
        return res.data
    except Exception as e:
        print(f"Error saving approval: {e}")
        return None

# ==========================================
# ANALYTICS & USAGE LOGGING
# ==========================================
def log_usage(user_id: str, module_name: str):
    try:
        supabase_admin.table("usage_logs").insert({
            "user_id": user_id,
            "module_name": module_name
        }).execute()
    except Exception as e:
        print(f"Error logging usage: {e}")

def get_usage_stats(user_id: str):
    try:
        # Get total generations (count all logs)
        total_res = supabase_admin.table("usage_logs").select("id", count="exact").eq("user_id", user_id).execute()
        total_generations = total_res.count if total_res.count else 0
        
        # Get leads found (count 'leadgen' logs)
        leads_res = supabase_admin.table("usage_logs").select("id", count="exact").eq("user_id", user_id).eq("module_name", "leadgen").execute()
        total_leads = leads_res.count if leads_res.count else 0
        
        # Get emails sent (count 'response' logs)
        emails_res = supabase_admin.table("usage_logs").select("id", count="exact").eq("user_id", user_id).eq("module_name", "response").execute()
        emails_sent = emails_res.count if emails_res.count else 0
        
        return {
            "total_generations": total_generations,
            "total_leads": total_leads,
            "emails_sent": emails_sent
        }
    except Exception as e:
        print(f"Error getting stats: {e}")
        return {"total_generations": 0, "total_leads": 0, "emails_sent": 0}

# ==========================================
# TELEGRAM ALERTS
# ==========================================
def send_telegram_alert(message: str):
    """Sends a notification to the admin Telegram chat."""
    try:
        bot_token = os.getenv("SYSTEM_TELEGRAM_BOT_TOKEN")
        chat_id = os.getenv("SYSTEM_TELEGRAM_CHAT_ID")
        
        if not bot_token or not chat_id:
            print("⚠️ Telegram alerts skipped: Missing SYSTEM_TELEGRAM_BOT_TOKEN or SYSTEM_TELEGRAM_CHAT_ID")
            return
            
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML"
        }
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        print(f"Failed to send Telegram alert: {e}")        