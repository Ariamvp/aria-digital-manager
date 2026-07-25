import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

url: str = os.getenv("SUPABASE_URL")
key: str = os.getenv("SUPABASE_ANON_KEY")
service_key: str = os.getenv("SUPABASE_SERVICE_KEY")

# Public client for user actions
supabase: Client = create_client(url, key)

# Admin client for backend tasks
supabase_admin: Client = create_client(url, service_key)

def get_user_settings(user_id: str):
    """Fetches the logged-in user's business settings."""
    response = supabase.table("business_settings").select("*").eq("user_id", user_id).execute()
    if response.data:
        return response.data[0]
    return None

def save_user_settings(user_id: str, settings: dict):
    """Saves or updates the user's business settings."""
    existing = get_user_settings(user_id)
    if existing:
        supabase.table("business_settings").update(settings).eq("user_id", user_id).execute()
    else:
        settings['user_id'] = user_id
        supabase.table("business_settings").insert(settings).execute()

def save_approval(user_id: str, task_type: str, to_address: str, subject: str, body: str):
    """Saves a draft approval to the database."""
    data = {
        "user_id": user_id,
        "task_type": task_type,
        "to_address": to_address,
        "subject": subject,
        "body": body,
        "status": "pending"
    }
    supabase.table("lead_approvals").insert(data).execute()