import os
from supabase import create_client, Client
from dotenv import load_dotenv
from cryptography.fernet import Fernet

load_dotenv()

# ==========================================
# SUPABASE CONFIG
# ==========================================
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(url, key)

# Admin client (for bypassing RLS)
admin_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
supabase_admin: Client = create_client(url, admin_key)

# ==========================================
# ENCRYPTION CONFIG
# ==========================================
# Paste the key you generated in Step 2 inside your .env file as ENCRYPTION_KEY
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")
if not ENCRYPTION_KEY:
    raise ValueError("ENCRYPTION_KEY is missing from your .env file!")

fernet = Fernet(ENCRYPTION_KEY)

def encrypt_text(plain_text: str) -> str:
    if not plain_text: return ""
    return fernet.encrypt(plain_text.encode()).decode()

def decrypt_text(encrypted_text: str) -> str:
    if not encrypted_text: return ""
    try:
        return fernet.decrypt(encrypted_text.encode()).decode()
    except Exception:
        # Fallback: If it fails, it means it was saved as plain text before encryption was added
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
        # Encrypt sensitive fields before saving
        sensitive_fields = ['gmail_app_password', 'telegram_bot_token', 'telegram_chat_id']
        for field in sensitive_fields:
            if field in settings_data and settings_data[field]:
                settings_data[field] = encrypt_text(settings_data[field])
        
        # Upsert (update if exists, insert if not)
        res = supabase_admin.table("business_settings").upsert(
            {"user_id": user_id, **settings_data}
        ).execute()
        return res.data
    except Exception as e:
        print(f"Error saving settings: {e}")
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