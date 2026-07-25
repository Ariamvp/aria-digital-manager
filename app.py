import os
import json
import re
import logging
import requests
import uuid
import streamlit as st
from dotenv import load_dotenv
from crewai import Agent, Task, Crew, Process, LLM
from crewai_tools import TavilySearchTool, ScrapeWebsiteTool
from db import supabase, supabase_admin, get_user_settings, save_user_settings, save_approval

# ==========================================
# 1. INITIALIZATION
# ==========================================
load_dotenv()
st.set_page_config(page_title="A.R.I.A. SaaS", page_icon="🤖", layout="wide")

# Helper: Quick Copy Button
def add_quick_copy(text):
    safe_text = text.replace("\\", "\\\\").replace("'", "\\'").replace("`", "\\`").replace("\n", "\\n").replace("\r", "")
    btn_id = f"btn_{uuid.uuid4().hex[:8]}"
    st.markdown(
        f"""
        <button id="{btn_id}" style="background-color: #f0f2f6; border: 1px solid #ccc; padding: 6px 12px; border-radius: 5px; cursor: pointer; font-size: 13px; margin-bottom: 10px;">
            📋 Copy to Clipboard
        </button>
        <script>
            document.getElementById("{btn_id}").onclick = function() {{
                navigator.clipboard.writeText('{safe_text}');
                this.innerHTML = "✅ Copied!";
                this.style.backgroundColor = "#d4edda";
                setTimeout(() => {{ this.innerHTML = "📋 Copy to Clipboard"; this.style.backgroundColor = "#f0f2f6"; }}, 2000);
            }};
        </script>
        """,
        unsafe_allow_html=True
    )

# ==========================================
# 2. AUTHENTICATION & TRIAL LOGIC
# ==========================================
def login_page():
    st.title("🤖 Welcome to A.R.I.A.")
    st.markdown("Your Autonomous Revenue & Intelligence Agent.")
    
    tab_login, tab_signup = st.tabs(["Login", "Sign Up"])
    
    with tab_login:
        with st.form("login_form"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Login", use_container_width=True)
            
            if submit:
                try:
                    res = supabase.auth.sign_in_with_password({"email": email, "password": password})
                    st.session_state['user'] = res.user
                    st.session_state['session'] = res.session
                    st.rerun()
                except Exception as e:
                    st.error(f"Login failed: {str(e)}")

    with tab_signup:
        with st.form("signup_form"):
            name = st.text_input("Full Name")
            email = st.text_input("Email")
            password = st.text_input("Password (min 6 chars)", type="password")
            submit = st.form_submit_button("Create Account & Start 14-Day Trial", use_container_width=True)
            
            if submit:
                try:
                    res = supabase.auth.sign_up({"email": email, "password": password, "options": {"data": {"full_name": name}}})
                    st.success("Account created! Please check your email to confirm, then log in.")
                except Exception as e:
                    st.error(f"Signup failed: {str(e)}")

def check_trial(user):
    """Checks if the user is still in their 14-day free trial."""
    res = supabase_admin.table("profiles").select("trial_ends_at").eq("id", user.id).execute()
    if res.data:
        # In a real app, parse the date and compare. For now, we just check if the row exists.
        return True 
    return False

# ==========================================
# 3. CREW DEFINITIONS (Dynamic)
# ==========================================
@st.cache_resource
def create_lead_crew():
    llm = LLM(model="gpt-4o")
    tavily_tool = TavilySearchTool()
    
    finder = Agent(role="Lead Discovery Specialist", goal="Find {category} in {location}.", backstory="Expert B2B lead finder.", llm=llm, tools=[tavily_tool], verbose=False)
    writer = Agent(role="Outreach Copywriter", goal="Draft warm B2B emails.", backstory="Expert in local partnerships.", llm=llm, verbose=False)

    return Crew(agents=[finder, writer],
                tasks=[
                    Task(description="Find 3 {category} in {location}. Extract company, website, contact name, email.", expected_output="List of leads.", agent=finder),
                    Task(description="Draft a partnership email to {contact_name} at {company}. PITCH: {business_pitch}. Sign as: {contact_info}.", expected_output="Email draft.", agent=writer)
                ], process=Process.sequential, verbose=False)

@st.cache_resource
def create_whatsapp_crew():
    llm = LLM(model="gpt-4o")
    expert = Agent(role="WhatsApp Expert", goal="Create engaging WhatsApp broadcasts.", backstory="Master of WhatsApp marketing.", llm=llm, verbose=False)
    return Crew(agents=[expert], tasks=[
        Task(description="Create a WhatsApp broadcast for {business_name}. Type: {broadcast_type}. Details: {specific_details}. Contact: {contact_info}. Use *bold* and emojis.", expected_output="WhatsApp message.", agent=expert)
    ], process=Process.sequential, verbose=False)

# ==========================================
# MAIN APP LOGIC
# ==========================================
if 'user' not in st.session_state:
    login_page()
    st.stop()

# Check Trial
if not check_trial(st.session_state['user']):
    st.error("Your 14-day free trial has expired. Please upgrade.")
    st.stop()

# Fetch User Settings
user_settings = get_user_settings(st.session_state['user'].id)
if user_settings is None:
    user_settings = {} 

# Sidebar
with st.sidebar:
    st.header(f" {st.session_state['user'].email}")
    st.caption("14-Day Free Trial Active")
    st.divider()
    if st.button("Logout"):
        supabase.auth.sign_out()
        st.session_state.clear()
        st.rerun()

st.title("🤖 A.R.I.A. Command Center")

# Tabs
tab_settings, tab_manual, tab_lead, tab_whatsapp = st.tabs([
    "⚙️ My Business Settings", 
    "📖 User Manual", 
    " Local Lead Gen", 
    "📱 WhatsApp Broadcasts"
])

# --- TAB: BUSINESS SETTINGS ---
with tab_settings:
    st.header("⚙️ Configure Your Business Profile")
    st.markdown("A.R.I.A. uses these details to personalize all your leads, emails, and broadcasts.")
    
    with st.form("settings_form"):
        col1, col2 = st.columns(2)
        with col1:
            biz_name = st.text_input("Business Name *", value=user_settings.get('business_name', ''))
            industry = st.selectbox("Industry", ["Hospitality", "Food/FMCG", "Service", "Retail", "Other"], index=0)
            location = st.text_input("Primary Location *", value=user_settings.get('location', ''))
        with col2:
            contact_info = st.text_input("Contact Info (Name | Phone | Email) *", value=user_settings.get('contact_info', ''))
            biz_pitch = st.text_area("Core Pitch (What do you sell?) *", height=100, value=user_settings.get('business_pitch', ''))
            
        st.subheader("🔐 API Credentials (Required for Automation)")
        st.caption("These are encrypted and only used to run your AI agents.")
        col3, col4 = st.columns(2)
        with col3:
            gmail_pw = st.text_input("Gmail App Password", type="password", value=user_settings.get('gmail_app_password', ''))
            tg_token = st.text_input("Telegram Bot Token", type="password", value=user_settings.get('telegram_bot_token', ''))
        with col4:
            tg_chat = st.text_input("Telegram Chat ID", value=user_settings.get('telegram_chat_id', ''))
            oa_key = st.text_input("OpenAI API Key", type="password", value=user_settings.get('openai_api_key', ''))
            tavily_key = st.text_input("Tavily API Key", type="password", value=user_settings.get('tavily_api_key', ''))

        if st.form_submit_button("💾 Save Settings", type="primary", use_container_width=True):
            settings_data = {
                "business_name": biz_name, "industry": industry, "location": location,
                "contact_info": contact_info, "business_pitch": biz_pitch,
                "gmail_app_password": gmail_pw, "telegram_bot_token": tg_token,
                "telegram_chat_id": tg_chat, "openai_api_key": oa_key, "tavily_api_key": tavily_key
            }
            save_user_settings(st.session_state['user'].id, settings_data)
            st.success("✅ Settings saved! A.R.I.A. is now configured for your business.")
            st.rerun()

# --- TAB: USER MANUAL ---
with tab_manual:
    st.header("📖 How to Use A.R.I.A.")
    st.markdown("""
    Welcome to your new AI workforce! Here is how to get the most out of A.R.I.A.:
    
    1. **Start Here:** Go to the **My Business Settings** tab. Fill out your business name, pitch, and API keys. A.R.I.A. cannot work without this!
    2. **Find Clients:** Use the **Local Lead Gen** tab. A.R.I.A. will search the web for businesses in your area and write personalized emails to them.
    3. **Engage Customers:** Use the **WhatsApp Broadcasts** tab to send offers to your existing customers.
    4. **Approve Actions:** If you enabled Telegram, A.R.I.A. will send drafts to your phone. Reply `send [ID]` to approve them.
    
    **Need Help?** Your 14-day trial gives you full access to all features.
    """)

# --- TAB: LOCAL LEAD GEN ---
with tab_lead:
    st.header("🎯 Automated Lead Discovery")
    
    if not user_settings.get('business_name') or not user_settings.get('business_pitch'):
        st.warning("⚠️ Please fill out your Business Name and Pitch in the 'My Business Settings' tab first!")
    else:
        st.info(f"Using your business profile: **{user_settings['business_name']}**")
        
        with st.form("lead_form"):
            category = st.text_input("Target Category (e.g., Tour Operators, Supermarkets)", value="tour operators")
            location_search = st.text_input("Target Location", value=user_settings.get('location', 'Kerala'))
            
            if st.form_submit_button("🔍 Find Leads", type="primary", use_container_width=True):
                st.write("🤖 A.R.I.A. is searching... (This takes 2-3 minutes)")
                try:
                    crew = create_lead_crew()
                    # We pass the user's settings into the AI
                    result = crew.kickoff(inputs={
                        "category": category, 
                        "location": location_search,
                        "business_pitch": user_settings['business_pitch'],
                        "contact_info": user_settings['contact_info'],
                        "company": "Target Company", # Placeholder for the loop
                        "contact_name": "Manager"
                    })
                    st.success("✅ Leads Found!")
                    add_quick_copy(result.raw)
                    st.markdown(result.raw)
                except Exception as e:
                    st.error(f"Error: {e}")

# --- TAB: WHATSAPP ---
with tab_whatsapp:
    st.header("📱 WhatsApp Broadcast Generator")
    
    if not user_settings.get('business_name'):
        st.warning("⚠️ Please fill out your Business Settings first!")
    else:
        with st.form("wa_form"):
            broadcast_type = st.selectbox("Type", ["Special Offer", "Festival Greeting", "Welcome Back"])
            details = st.text_area("Specific Offer Details")
            
            if st.form_submit_button("✨ Generate", type="primary"):
                st.write("Generating...")
                try:
                    crew = create_whatsapp_crew()
                    result = crew.kickoff(inputs={
                        "business_name": user_settings['business_name'],
                        "broadcast_type": broadcast_type,
                        "specific_details": details,
                        "contact_info": user_settings['contact_info']
                    })
                    st.success("✅ Message Generated!")
                    add_quick_copy(result.raw)
                    st.code(result.raw, language="text")
                except Exception as e:
                    st.error(f"Error: {e}")