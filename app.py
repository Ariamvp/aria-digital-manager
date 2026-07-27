import os
import json
import re
import uuid
from datetime import datetime, timezone
import streamlit as st
from dotenv import load_dotenv
from crewai import Agent, Task, Crew, Process, LLM
from crewai_tools import TavilySearchTool, ScrapeWebsiteTool
from db import supabase, supabase_admin, get_user_settings, save_user_settings

# ==========================================
# 1. INITIALIZATION & THEME
# ==========================================
load_dotenv()
st.set_page_config(page_title="A.R.I.A. Command Center", page_icon="🔥", layout="wide", initial_sidebar_state="expanded")

# Session State for Navigation
if 'page' not in st.session_state:
    st.session_state['page'] = 'dashboard'

# ==========================================
# 2. CUSTOM CSS - PROFESSIONAL DASHBOARD
# ==========================================
st.markdown("""
<style>
    /* === GLOBAL === */
    .stApp { background-color: #F8FAFC; font-family: 'Inter', -apple-system, sans-serif; }
    
    /* === SIDEBAR (DARK) === */
    section[data-testid="stSidebar"] {
        background-color: #0F172A !important;
        border-right: 1px solid #1E293B;
    }
    section[data-testid="stSidebar"] .stMarkdown { color: #F8FAFC !important; }
    section[data-testid="stSidebar"] label { color: #CBD5E1 !important; font-size: 13px; }
    section[data-testid="stSidebar"] .stSelectbox label { color: #94A3B8 !important; font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; }
    
    /* Sidebar Inputs */
    section[data-testid="stSidebar"] .stSelectbox > div > div > div {
        background-color: #1E293B !important; color: #F8FAFC !important; border: 1px solid #334155 !important;
    }
    
    /* === MAIN AREA === */
    .main-header { 
        display: flex; justify-content: space-between; align-items: center; 
        margin-bottom: 32px; padding-bottom: 20px; border-bottom: 1px solid #E2E8F0; 
    }
    .page-title { font-size: 28px; font-weight: 700; color: #0F172A; margin: 0; }
    .page-subtitle { font-size: 15px; color: #64748B; margin-top: 8px; }
    
    /* === CARDS === */
    .dashboard-card {
        background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 12px; 
        padding: 28px; margin-bottom: 24px; box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    }
    .card-header {
        display: flex; align-items: center; justify-content: space-between; 
        margin-bottom: 24px; padding-bottom: 16px; border-bottom: 1px solid #F1F5F9;
    }
    .card-title { font-size: 18px; font-weight: 700; color: #0F172A; display: flex; align-items: center; gap: 12px; }
    .card-icon { 
        width: 36px; height: 36px; background: #F0FDF4; border-radius: 8px; 
        display: flex; align-items: center; justify-content: center; font-size: 18px;
    }
    .card-badge { font-size: 12px; color: #16A34A; font-weight: 600; display: flex; align-items: center; gap: 6px; }
    
    /* === FORMS === */
    .stTextInput > div > div > input, .stTextArea > div > div > textarea, .stSelectbox > div > div > div {
        background-color: #FFFFFF !important; color: #0F172A !important; 
        border: 1px solid #E2E8F0 !important; border-radius: 8px !important;
    }
    .stTextInput > div > div > input:focus, .stTextArea > div > div > textarea:focus {
        border-color: #16A34A !important; box-shadow: 0 0 0 3px rgba(22, 163, 74, 0.1) !important;
    }
    .stTextInput label, .stTextArea label, .stSelectbox label {
        color: #374151 !important; font-weight: 600 !important; font-size: 14px !important;
    }
    
    /* === BUTTONS (GREEN) === */
    .stButton > button[kind="primary"] {
        background-color: #16A34A !important; color: #FFFFFF !important; 
        border: none !important; border-radius: 8px !important; font-weight: 600 !important;
        padding: 10px 24px !important; transition: all 0.2s !important;
    }
    .stButton > button[kind="primary"]:hover {
        background-color: #15803D !important; transform: translateY(-1px) !important;
        box-shadow: 0 4px 12px rgba(22, 163, 74, 0.3) !important;
    }
    .stButton > button[kind="secondary"] {
        background-color: transparent !important; color: #64748B !important; 
        border: 1px solid #E2E8F0 !important; border-radius: 8px !important;
    }
    
    /* === METRICS === */
    .metric-card {
        background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 12px; 
        padding: 20px; text-align: left;
    }
    .metric-label { font-size: 13px; color: #64748B; font-weight: 500; margin-bottom: 8px; }
    .metric-value { font-size: 28px; font-weight: 700; color: #0F172A; }
    .metric-trend { font-size: 12px; color: #16A34A; font-weight: 600; margin-top: 4px; }
    
    /* Hide Streamlit defaults */
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    
    /* Sidebar Section Headers */
    .sidebar-section { 
        color: #16A34A !important; font-size: 11px; font-weight: 700; 
        letter-spacing: 1px; text-transform: uppercase; margin-top: 24px; margin-bottom: 8px; 
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 3. AUTHENTICATION
# ==========================================
def login_page():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown('<div style="text-align:center; margin-top: 100px;">', unsafe_allow_html=True)
        st.markdown('<div style="font-size: 48px; margin-bottom: 10px;">🔥</div>', unsafe_allow_html=True)
        st.title("A.R.I.A. Command Center")
        st.markdown('<p style="color: #64748B; margin-bottom: 32px;">Autonomous Revenue & Intelligence Agent</p>', unsafe_allow_html=True)
        
        tab_login, tab_signup = st.tabs(["Login", "Sign Up"])
        
        with tab_login:
            email = st.text_input("Email", key="login_email")
            password = st.text_input("Password", type="password", key="login_password")
            if st.button("Login", type="primary", use_container_width=True):
                try:
                    res = supabase.auth.sign_in_with_password({"email": email, "password": password})
                    st.session_state['user'] = res.user
                    st.session_state['session'] = res.session
                    st.rerun()
                except Exception as e:
                    st.error(f"Login failed: {str(e)}")
        
        with tab_signup:
            name = st.text_input("Full Name", key="signup_name")
            email = st.text_input("Email", key="signup_email")
            password = st.text_input("Password (min 6 chars)", type="password", key="signup_password")
            if st.button("Create Account", type="primary", use_container_width=True):
                try:
                    res = supabase.auth.sign_up({"email": email, "password": password, "options": {"data": {"full_name": name}}})
                    st.success("Account created! Check your email.")
                except Exception as e:
                    st.error(f"Signup failed: {str(e)}")

def check_trial(user):
    try:
        res = supabase_admin.table("profiles").select("trial_ends_at, role").eq("id", user.id).execute()
        if not res.data: return True
        user_data = res.data[0]
        if user_data.get('role') == 'admin': return True
        trial_end = user_data.get('trial_ends_at')
        if trial_end:
            trial_end_dt = datetime.fromisoformat(trial_end.replace('Z', '+00:00'))
            if datetime.now(timezone.utc) < trial_end_dt: return True
        return False
    except: return True

def get_user_role(user_id):
    try:
        res = supabase_admin.table("profiles").select("role").eq("id", user_id).execute()
        if res.data: return res.data[0].get('role', 'user')
        return 'user'
    except: return 'user'

# ==========================================
# 4. CREW DEFINITIONS
# ==========================================
@st.cache_resource
def create_negotiation_crew():
    llm = LLM(model="gpt-4o")
    tavily_tool = TavilySearchTool()
    researcher = Agent(role="Pricing Analyst", goal="Find competitor pricing.", backstory="Expert analyst.", llm=llm, tools=[tavily_tool], verbose=False)
    strategist = Agent(role="Procurement Strategist", goal="Develop negotiation leverage.", backstory="Veteran expert.", llm=llm, verbose=False)
    drafter = Agent(role="Copywriter", goal="Draft professional email.", backstory="Specialist in vendor comms.", llm=llm, verbose=False)
    qa = Agent(role="QA Director", goal="Format as JSON.", backstory="Ensures JSON format.", llm=llm, verbose=False)
    return Crew(agents=[researcher, strategist, drafter, qa], tasks=[
        Task(description="Research {vendor_name} and {current_service}. Find 2-3 competitors with pricing.", expected_output="Competitor summary.", agent=researcher),
        Task(description="Develop strategy for {vendor_name}. We pay ${monthly_cost}/mo.", expected_output="Strategy.", agent=strategist),
        Task(description="Draft email to {vendor_name}. Sign as: {contact_info}", expected_output="Draft.", agent=drafter),
        Task(description='Output strict JSON: {"subject": "...", "body": "..."}', expected_output="JSON", agent=qa)
    ], process=Process.sequential, verbose=False)

@st.cache_resource
def create_repurposing_crew():
    llm = LLM(model="gpt-4o")
    analyst = Agent(role="Content Strategist", goal="Analyze source material.", backstory="Master strategist.", llm=llm, verbose=False)
    blog_writer = Agent(role="SEO Blog Writer", goal="Write SEO blog post.", backstory="Authoritative writer.", llm=llm, verbose=False)
    social_manager = Agent(role="Social Media Manager", goal="Create viral posts.", backstory="Social expert.", llm=llm, verbose=False)
    newsletter_writer = Agent(role="Email Expert", goal="Write newsletter.", backstory="High open-rate expert.", llm=llm, verbose=False)
    qa = Agent(role="Content QA", goal="Format as JSON.", backstory="JSON formatter.", llm=llm, verbose=False)
    return Crew(agents=[analyst, blog_writer, social_manager, newsletter_writer, qa], tasks=[
        Task(description="Analyze: {source_content}. Target: {target_audience}.", expected_output="Analysis.", agent=analyst),
        Task(description="Write 500-word SEO blog post.", expected_output="Blog.", agent=blog_writer),
        Task(description="Write LinkedIn post, Twitter thread, IG caption.", expected_output="Social.", agent=social_manager),
        Task(description="Write newsletter email.", expected_output="Newsletter.", agent=newsletter_writer),
        Task(description='Format ALL into JSON: {"blog": "...", "linkedin": "...", "twitter": "...", "instagram": "...", "newsletter": "..."}', expected_output="JSON", agent=qa)
    ], process=Process.sequential, verbose=False)

@st.cache_resource
def create_prospect_finder_crew():
    llm = LLM(model="gpt-4o")
    tavily_tool = TavilySearchTool()
    scrape_tool = ScrapeWebsiteTool()
    finder = Agent(role="Lead Discovery Specialist", goal="Find {category} in {location}.", backstory="Expert B2B lead finder.", llm=llm, tools=[tavily_tool, scrape_tool], verbose=False)
    qualifier = Agent(role="Lead Qualification Analyst", goal="Format leads as JSON.", backstory="Data formatter.", llm=llm, verbose=False)
    return Crew(agents=[finder, qualifier], tasks=[
        Task(description="Search for {category} in {location}. Find {num_leads} businesses. Extract: company, website, contact_name, contact_title, email.", expected_output="JSON array of leads", agent=finder),
        Task(description="Format leads into strict JSON array.", expected_output="JSON", agent=qualifier)
    ], process=Process.sequential, verbose=False)

@st.cache_resource
def create_response_crew():
    llm = LLM(model="gpt-4o")
    writer = Agent(role="Hospitality Specialist", goal="Create Property Profile AND email.", backstory="Partnership expert.", llm=llm, verbose=False)
    return Crew(agents=[writer], tasks=[
        Task(description="""
        You received: {incoming_request}
        Business details: {raw_business_details}
        Generate TWO things:
        === PART 1: PROPERTY PROFILE ===
        # 🏨 PROPERTY PROFILE: {business_name}
        ## 📍 Location, ️ Rooms, 💰 Rates, 🍽️ Meals, ✨ Amenities, 📸 Photos, 🌟 Offers, 🗺️ Nearby
        === PART 2: EMAIL ===
        Write short email (<100 words):
        1. Extract sender name. If blank, use "Valued Partner".
        2. Start "Dear [Name],"
        3. Thank them for interest in {business_name}.
        4. Say "Please find our detailed Property Profile above."
        5. Sign off professionally using: {contact_info}
        OUTPUT: Profile first, then "---EMAIL---" marker, then email.
        """, expected_output="Profile + ---EMAIL--- + Email", agent=writer)
    ], process=Process.sequential, verbose=False)

@st.cache_resource
def create_review_crew():
    llm = LLM(model="gpt-4o")
    responder = Agent(role="Reputation Manager", goal="Write review responses.", backstory="Guest relations expert.", llm=llm, verbose=False)
    return Crew(agents=[responder], tasks=[
        Task(description="""
        Respond to this {sentiment} review.
        Reviewer: {reviewer_name}
        Review: "{review_text}"
        RULES:
        - If POSITIVE: Thank warmly, mention specifics, invite back
        - If NEGATIVE: Apologize sincerely, validate concern, offer offline resolution
        - Keep under 150 words. Sign as: {contact_info}
        """, expected_output="Professional response", agent=responder)
    ], process=Process.sequential, verbose=False)

@st.cache_resource
def create_whatsapp_crew():
    llm = LLM(model="gpt-4o")
    expert = Agent(role="WhatsApp Marketing Specialist", goal="Create engaging broadcasts.", backstory="WhatsApp expert.", llm=llm, verbose=False)
    return Crew(agents=[expert], tasks=[
        Task(description="""
        Create WhatsApp broadcast for {business_name}.
        Type: {broadcast_type}
        Details: {specific_details}
        Contact: {contact_info}
        RULES: Use *asterisks* for bold, emojis (1-2 per line max), keep under 150 words, include clear CTA, add "Reply STOP to unsubscribe".
        """, expected_output="WhatsApp message", agent=expert)
    ], process=Process.sequential, verbose=False)

def parse_json_output(raw_output):
    try:
        cleaned = re.sub(r'^```json\s*|\s*```$', '', raw_output.strip(), flags=re.MULTILINE)
        return json.loads(cleaned)
    except:
        return {"subject": "Error", "body": raw_output}


# Initialize chat history
if 'chat_history' not in st.session_state:
    st.session_state['chat_history'] = []

# ==========================================
# 5. MAIN APP LOGIC
# ==========================================
if 'user' not in st.session_state:
    login_page()
    st.stop()

if not check_trial(st.session_state['user']):
    st.error("Your 14-day free trial has expired. Please upgrade.")
    st.stop()

user_settings = get_user_settings(st.session_state['user'].id) or {}
user_role = get_user_role(st.session_state['user'].id)
user_email = st.session_state['user'].email

# ==========================================
# 6. SIDEBAR NAVIGATION
# ==========================================
with st.sidebar:
    # Brand
    st.markdown('<div style="display:flex; align-items:center; gap:12px; padding:10px 0 24px; border-bottom:1px solid #1E293B; margin-bottom:24px;">', unsafe_allow_html=True)
    st.markdown('<div style="font-size:24px;">🔥</div>', unsafe_allow_html=True)
    st.markdown('<div><div style="font-size:18px; font-weight:700; color:#F8FAFC;">A.R.I.A</div><div style="font-size:10px; color:#16A34A; font-weight:600; letter-spacing:1px;">COMMAND CENTER</div></div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Navigation
    st.markdown('<div class="sidebar-section">Dashboard</div>', unsafe_allow_html=True)
    if st.button(" Dashboard", use_container_width=True, type="primary" if st.session_state['page'] == 'dashboard' else "secondary"):
        st.session_state['page'] = 'dashboard'; st.rerun()
    
    st.markdown('<div class="sidebar-section">Business</div>', unsafe_allow_html=True)
    if st.button("🏢 Business Profile", use_container_width=True, type="primary" if st.session_state['page'] == 'business' else "secondary"):
        st.session_state['page'] = 'business'; st.rerun()
    if st.button("👥 Team Members", use_container_width=True, type="primary" if st.session_state['page'] == 'team' else "secondary"):
        st.session_state['page'] = 'team'; st.rerun()
    
    st.markdown('<div class="sidebar-section">AI Tools</div>', unsafe_allow_html=True)
    if st.button(" AI Chat", use_container_width=True, type="primary" if st.session_state['page'] == 'ai_chat' else "secondary"):
        st.session_state['page'] = 'ai_chat'; st.rerun()
    if st.button(" Negotiator", use_container_width=True, type="primary" if st.session_state['page'] == 'vendor' else "secondary"):
        st.session_state['page'] = 'vendor'; st.rerun()
    if st.button("🎨 Content Studio", use_container_width=True, type="primary" if st.session_state['page'] == 'content' else "secondary"):
        st.session_state['page'] = 'content'; st.rerun()
    if st.button("✉️ Response Writer", use_container_width=True, type="primary" if st.session_state['page'] == 'response' else "secondary"):
        st.session_state['page'] = 'response'; st.rerun()
    if st.button("🎯 Lead Finder", use_container_width=True, type="primary" if st.session_state['page'] == 'leadgen' else "secondary"):
        st.session_state['page'] = 'leadgen'; st.rerun()
    if st.button("📱 WhatsApp Studio", use_container_width=True, type="primary" if st.session_state['page'] == 'whatsapp' else "secondary"):
        st.session_state['page'] = 'whatsapp'; st.rerun()
    if st.button("⭐ Review Responses", use_container_width=True, type="primary" if st.session_state['page'] == 'review' else "secondary"):
        st.session_state['page'] = 'review'; st.rerun()
    
    st.markdown('<div class="sidebar-section">Integrations</div>', unsafe_allow_html=True)
    if st.button("🔑 API Keys", use_container_width=True, type="primary" if st.session_state['page'] == 'api' else "secondary"):
        st.session_state['page'] = 'api'; st.rerun()
    
    st.markdown('<div class="sidebar-section">Help</div>', unsafe_allow_html=True)
    if st.button("📖 User Manual", use_container_width=True, type="primary" if st.session_state['page'] == 'manual' else "secondary"):
        st.session_state['page'] = 'manual'; st.rerun()
    
    st.divider()
    
    # User Profile
    st.markdown(f'<div style="display:flex; align-items:center; gap:12px; padding:12px; background:#1E293B; border-radius:8px; margin-bottom:12px;">', unsafe_allow_html=True)
    st.markdown(f'<div style="width:36px; height:36px; background:#16A34A; border-radius:50%; display:flex; align-items:center; justify-content:center; font-weight:700; color:white;">{user_email[0].upper()}</div>', unsafe_allow_html=True)
    st.markdown(f'<div><div style="font-size:13px; font-weight:600; color:#F8FAFC;">{user_email.split("@")[0]}</div><div style="font-size:11px; color:#16A34A;">{"Admin" if user_role == "admin" else "Free Trial"}</div></div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    
    if st.button("🚪 Logout", use_container_width=True, type="secondary"):
        supabase.auth.sign_out()
        st.session_state.clear()
        st.rerun()

# ==========================================
# 7. PAGE ROUTER
# ==========================================
page = st.session_state['page']

# Helper for Page Header
def page_header(title, subtitle, breadcrumb=""):
    st.markdown(f'<div class="main-header">', unsafe_allow_html=True)
    st.markdown(f'<div><h1 class="page-title">{title}</h1><p class="page-subtitle">{subtitle}</p></div>', unsafe_allow_html=True)
    if breadcrumb:
        st.markdown(f'<div style="font-size:13px; color:#64748B;">{breadcrumb}</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# --- DASHBOARD ---
if page == 'dashboard':
    page_header("Dashboard", "Welcome back! Here's what's happening with your business today.", "Home › Dashboard")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown('<div class="metric-card"><div class="metric-label">Total Leads</div><div class="metric-value">247</div><div class="metric-trend">↑ 12% this week</div></div>', unsafe_allow_html=True)
    with col2:
        st.markdown('<div class="metric-card"><div class="metric-label">AI Generations</div><div class="metric-value">1,429</div><div class="metric-trend">↑ 24% this week</div></div>', unsafe_allow_html=True)
    with col3:
        st.markdown('<div class="metric-card"><div class="metric-label">Emails Sent</div><div class="metric-value">89</div><div class="metric-trend">↑ 8% this week</div></div>', unsafe_allow_html=True)
    with col4:
        st.markdown('<div class="metric-card"><div class="metric-label">Cost Savings</div><div class="metric-value">₹18,400</div><div class="metric-trend">↑ 15% this month</div></div>', unsafe_allow_html=True)
    
    st.markdown('<div class="dashboard-card" style="margin-top:24px;"><h3 style="margin:0 0 16px 0; color:#0F172A;">Recent Activity</h3><p style="color:#64748B;">Your AI agents are working autonomously. Check the modules below to see drafts and approvals.</p></div>', unsafe_allow_html=True)

# --- BUSINESS PROFILE ---
elif page == 'business':
    page_header("Business Profile", "Configure your business details to personalize all AI outputs.", "Home › Business › Business Profile")
    
    # Card 1: Business Info
    st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
    st.markdown('<div class="card-header"><div class="card-title"><div class="card-icon">🏢</div>Business Information</div><div class="card-badge">🔒 Used across all AI tools</div></div>', unsafe_allow_html=True)
    
    with st.form("business_form"):
        col1, col2 = st.columns(2)
        with col1:
            biz_name = st.text_input("Business Name *", value=user_settings.get('business_name', ''))
            industry = st.selectbox("Industry", ["Hospitality", "Food/FMCG", "Service", "Retail", "Other"], index=0)
            location = st.text_input("Primary Location *", value=user_settings.get('location', ''))
        with col2:
            contact_info = st.text_input("Contact Info (Name | Phone | Email) *", value=user_settings.get('contact_info', ''))
            biz_pitch = st.text_area("Core Pitch *", height=100, value=user_settings.get('business_pitch', ''))
        
        st.markdown('</div><div class="dashboard-card" style="margin-top:24px;">', unsafe_allow_html=True)
        st.markdown('<div class="card-header"><div class="card-title"><div class="card-icon">🔑</div>Integration Credentials</div><div class="card-badge">🛡️ Encrypted and secure</div></div>', unsafe_allow_html=True)
        
        col3, col4 = st.columns(2)
        with col3:
            gmail_pw = st.text_input("Gmail App Password", type="password", value=user_settings.get('gmail_app_password', ''))
            tg_token = st.text_input("Telegram Bot Token", type="password", value=user_settings.get('telegram_bot_token', ''))
        with col4:
            tg_chat = st.text_input("Telegram Chat ID", value=user_settings.get('telegram_chat_id', ''))
        
        if st.form_submit_button("💾 Save Settings", type="primary"):
            save_user_settings(st.session_state['user'].id, {
                "business_name": biz_name, "industry": industry, "location": location,
                "contact_info": contact_info, "business_pitch": biz_pitch,
                "gmail_app_password": gmail_pw, "telegram_bot_token": tg_token,
                "telegram_chat_id": tg_chat
            })
            st.success("✅ Settings saved successfully!")
            st.rerun()
        
        st.markdown('<div style="background:#F0FDF4; border:1px solid #BBF7D0; border-radius:8px; padding:12px 16px; margin-top:20px; font-size:13px; color:#166534; display:flex; align-items:center; gap:8px;"><span>ℹ️</span> These credentials enable A.R.I.A to connect with your platforms and perform automated tasks.</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

# --- AI TOOLS ---
elif page == 'vendor':
    page_header("Negotiator", "Lower your business costs with data-driven negotiation emails.", "Home › AI Tools › Negotiator")
    st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
    if not user_settings.get('contact_info'):
        st.warning("⚠️ Complete Business Profile first!")
    else:
        with st.form("vendor_form"):
            col1, col2 = st.columns(2)
            with col1:
                v_name = st.text_input("Vendor Name")
                v_service = st.text_input("Current Service")
            with col2:
                v_cost = st.text_input("Monthly Cost ($)")
                v_date = st.text_input("Contract End Date")
            if st.form_submit_button("🚀 Generate Negotiation Email", type="primary"):
                with st.spinner("Researching..."):
                    crew = create_negotiation_crew()
                    result = crew.kickoff(inputs={"vendor_name": v_name, "current_service": v_service, "monthly_cost": v_cost, "contract_end_date": v_date, "contact_info": user_settings['contact_info']})
                    parsed = parse_json_output(result.raw)
                    st.success("✅ Draft Generated!")
                    st.code(parsed.get('body', ''), language="text")
    st.markdown('</div>', unsafe_allow_html=True)

elif page == 'content':
    page_header("Content Studio", "Turn one piece of content into a full week of marketing materials.", "Home › AI Tools › Content Studio")
    st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
    with st.form("content_form"):
        source = st.text_area("Source Material", height=150)
        audience = st.text_input("Target Audience")
        if st.form_submit_button("🔄 Repurpose Content", type="primary"):
            with st.spinner("Analyzing..."):
                crew = create_repurposing_crew()
                result = crew.kickoff(inputs={"source_content": source, "target_audience": audience})
                parsed = parse_json_output(result.raw)
                st.success("✅ Content Generated!")
                st.markdown(parsed.get('blog', ''))
    st.markdown('</div>', unsafe_allow_html=True)

elif page == 'leadgen':
    page_header("Lead Finder", "Find real businesses with verified emails in your target market.", "Home › AI Tools › Lead Finder")
    st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
    if not user_settings.get('business_pitch'):
        st.warning("⚠️ Complete Business Profile first!")
    else:
        with st.form("leadgen_form"):
            col1, col2 = st.columns(2)
            with col1: category = st.text_input("Target Category", value="boutique hotels")
            with col2: location_search = st.text_input("Location", value=user_settings.get('location', ''))
            num_leads = st.slider("Number of Leads", 3, 10, 5)
            if st.form_submit_button("🔍 Find Leads", type="primary"):
                with st.spinner("Searching..."):
                    crew = create_prospect_finder_crew()
                    result = crew.kickoff(inputs={"category": category, "location": location_search, "num_leads": num_leads})
                    st.success("✅ Leads Found!")
                    st.code(result.raw, language="json")
    st.markdown('</div>', unsafe_allow_html=True)

elif page == 'response':
    page_header("Response Writer", "Generate professional property profiles and reply emails.", "Home › AI Tools › Response Writer")
    st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
    with st.form("response_form"):
        incoming = st.text_area("Incoming Lead Request", height=100)
        raw_details = st.text_area("Your Business Details", height=150, value=user_settings.get('business_pitch', ''))
        if st.form_submit_button("✨ Generate Response", type="primary"):
            with st.spinner("Crafting..."):
                crew = create_response_crew()
                result = crew.kickoff(inputs={"incoming_request": incoming, "raw_business_details": raw_details, "business_name": user_settings.get('business_name', 'Your Business'), "contact_info": user_settings.get('contact_info', '')})
                st.success("✅ Generated!")
                parts = result.raw.split("---EMAIL---")
                st.markdown(parts[0])
                if len(parts) > 1:
                    st.divider()
                    st.markdown(parts[1])
    st.markdown('</div>', unsafe_allow_html=True)

elif page == 'whatsapp':
    page_header("WhatsApp Studio", "Create engaging WhatsApp broadcasts for your customer list.", "Home › AI Tools › WhatsApp Studio")
    st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
    if not user_settings.get('business_name'):
        st.warning("⚠️ Complete Business Profile first!")
    else:
        with st.form("whatsapp_form"):
            col1, col2 = st.columns(2)
            with col1: btype = st.selectbox("Broadcast Type", ["Special Offer", "Festival Greeting", "Welcome Back"])
            with col2: audience = st.selectbox("Target Audience", ["All Customers", "VIP Customers", "New Customers"])
            details = st.text_area("Offer Details", height=120)
            if st.form_submit_button("✨ Generate Broadcast", type="primary"):
                with st.spinner("Creating..."):
                    crew = create_whatsapp_crew()
                    result = crew.kickoff(inputs={"business_name": user_settings['business_name'], "broadcast_type": btype, "specific_details": details, "contact_info": user_settings.get('contact_info', '')})
                    st.success("✅ Broadcast Generated!")
                    st.code(result.raw, language="text")
    st.markdown('</div>', unsafe_allow_html=True)

elif page == 'review':
    page_header("Review Responses", "Instantly generate empathetic, brand-safe responses to reviews.", "Home › AI Tools › Review Responses")
    st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
    with st.form("review_form"):
        col1, col2 = st.columns(2)
        with col1: reviewer = st.text_input("Reviewer Name")
        with col2: sentiment = st.radio("Sentiment", ["Positive", "Negative", "Mixed"], horizontal=True)
        review_text = st.text_area("Review Text", height=120)
        if st.form_submit_button("✨ Generate Response", type="primary"):
            with st.spinner("Writing..."):
                crew = create_review_crew()
                result = crew.kickoff(inputs={"reviewer_name": reviewer, "review_text": review_text, "sentiment": sentiment, "contact_info": user_settings.get('contact_info', '')})
                st.success("✅ Response Generated!")
                st.markdown(result.raw)
    st.markdown('</div>', unsafe_allow_html=True)

# --- AI CHAT ---
elif page == 'ai_chat':
    page_header("AI Chat", "Ask ARIA anything about your business. Get instant AI assistance.", "Home › AI Tools › AI Chat")
    
    # Chat container
    st.markdown('<div class="dashboard-card" style="min-height: 500px;">', unsafe_allow_html=True)
    
    # Display chat history
    if st.session_state['chat_history']:
        for message in st.session_state['chat_history']:
            if message['role'] == 'user':
                st.markdown(f"""
                <div style="display:flex; justify-content:flex-end; margin-bottom:16px;">
                    <div style="background:#16A34A; color:white; padding:12px 16px; border-radius:12px 12px 0 12px; max-width:70%; font-size:14px;">
                        {message['content']}
                    </div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div style="display:flex; justify-content:flex-start; margin-bottom:16px;">
                    <div style="background:#F1F5F9; color:#0F172A; padding:12px 16px; border-radius:12px 12px 12px 0; max-width:70%; font-size:14px;">
                        {message['content']}
                    </div>
                </div>
                """, unsafe_allow_html=True)
    else:
        # Welcome message
        st.markdown("""
        <div style="text-align:center; padding:40px 20px;">
            <div style="font-size:48px; margin-bottom:16px;">🤖</div>
            <h2 style="color:#0F172A; margin-bottom:8px;">ARIA</h2>
            <p style="color:#64748B; font-size:16px;">How can I help?</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Suggestion chips
    st.markdown('<div style="margin-top:24px;">', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button(" Generate an Onam Campaign", use_container_width=True, type="secondary"):
            user_input = "Generate an Onam Campaign for my business"
            st.session_state['chat_history'].append({'role': 'user', 'content': user_input})
            
            # AI Response
            ai_response = f"""
**🎉 Onam Campaign for {user_settings.get('business_name', 'Your Business')}**

Here's a complete Onam campaign strategy:

**1. WhatsApp Broadcast:**
"🌸 Happy Onam! 

Celebrate this festival with special offers from {user_settings.get('business_name', 'our business')}!

🎁 **Special Onam Discount:** 20% off on all services
🍽️ **Festival Feast:** Traditional Onam sadhya available
 **Stay & Celebrate:** Book 2 nights, get 1 free

Valid till September 15th. 

Reply BOOK to reserve your spot!

Warm regards,
{user_settings.get('contact_info', 'Team ARIA')}

Reply STOP to unsubscribe"

**2. Social Media Posts:**
- Instagram: Carousel of Onam celebrations at your venue
- Facebook: Event page for Onam special events
- Stories: Behind-the-scenes of Onam preparations

**3. Email Newsletter:**
Subject: "🌸 Celebrate Onam with Special Offers!"

**4. Local Lead Outreach:**
Target: Tour operators in Kerala for Onam package partnerships

Would you like me to generate any of these in detail?
"""
            st.session_state['chat_history'].append({'role': 'assistant', 'content': ai_response})
            st.rerun()
        
        if st.button(" Find hotels in Kochi", use_container_width=True, type="secondary"):
            user_input = "Find hotels in Kochi"
            st.session_state['chat_history'].append({'role': 'user', 'content': user_input})
            
            ai_response = """
**🏨 Finding Hotels in Kochi**

I'll search for boutique hotels and resorts in Kochi for potential partnerships.

**Recommended Action:** Use the **Lead Finder** module for a comprehensive search with verified emails.

**Quick Preview:**
I can find:
- Boutique hotels (5-20 rooms)
- Heritage properties
- Resort chains
- Budget accommodations

**Suggested Search Parameters:**
- Category: "boutique hotels" or "heritage hotels"
- Location: "Kochi, Kerala"
- Number of leads: 5-10

👉 **Click "Lead Finder" in the sidebar** to run a full search with AI-powered email verification and contact details.

Would you like me to guide you through the Lead Finder module?
"""
            st.session_state['chat_history'].append({'role': 'assistant', 'content': ai_response})
            st.rerun()
    
    with col2:
        if st.button("⭐ Write reply to Google review", use_container_width=True, type="secondary"):
            user_input = "Write reply to Google review"
            st.session_state['chat_history'].append({'role': 'user', 'content': user_input})
            
            ai_response = """
**⭐ Google Review Response**

I can help you craft a professional, empathetic response to any Google review.

**To generate a response, I need:**
1. **Reviewer Name** (e.g., "John D.")
2. **Review Text** (copy-paste the review)
3. **Sentiment** (Positive, Negative, or Mixed)

**Example:**
If a customer wrote: *"Great food but slow service"*

I would generate:
*"Dear John, thank you for your feedback! We're delighted you enjoyed our food. We sincerely apologize for the wait time and are working to improve our service speed. We'd love to welcome you back for a better experience. Warm regards, [Your Name]"*

👉 **Click "Response Writer" in the sidebar** to generate a custom response.

Or paste the review here and I'll draft a response right now!
"""
            st.session_state['chat_history'].append({'role': 'assistant', 'content': ai_response})
            st.rerun()
        
        if st.button("📱 Create WhatsApp campaign", use_container_width=True, type="secondary"):
            user_input = "Create WhatsApp campaign"
            st.session_state['chat_history'].append({'role': 'user', 'content': user_input})
            
            ai_response = f"""
** WhatsApp Campaign Creator**

I'll help you create an engaging WhatsApp broadcast for your customers.

**Campaign Types:**
-  Special Offers & Discounts
- 🎉 Festival Greetings
- 👋 Welcome Back Messages
- 📢 New Product/Service Announcements

**To create your campaign, I need:**
1. **Campaign Type** (from above)
2. **Offer Details** (discount %, validity, terms)
3. **Target Audience** (All, VIP, New customers)

**Quick Example:**
*" Weekend Special! 🌟

Get 25% off on all bookings this weekend!

✅ Valid: Sat-Sun only
✅ Includes: Free breakfast
✅ Book by: Friday 6pm

Reply YES to book now!

{user_settings.get('business_name', 'Your Business')}
{user_settings.get('contact_info', 'Contact us')}

Reply STOP to unsubscribe"*

👉 **Click "WhatsApp Studio" in the sidebar** to generate a custom campaign.

Or tell me your offer details and I'll draft it here!
"""
            st.session_state['chat_history'].append({'role': 'assistant', 'content': ai_response})
            st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Chat input
    st.markdown('<div class="dashboard-card" style="margin-top:24px;">', unsafe_allow_html=True)
    with st.form("chat_input_form", clear_on_submit=True):
        user_message = st.text_input("Message ARIA...", placeholder="Type your question or request...", label_visibility="collapsed")
        col1, col2 = st.columns([6, 1])
        with col2:
            submitted = st.form_submit_button("Send", type="primary", use_container_width=True)
        
        if submitted and user_message:
            st.session_state['chat_history'].append({'role': 'user', 'content': user_message})
            
            # Simple AI response based on keywords
            msg_lower = user_message.lower()
            
            if 'onam' in msg_lower or 'campaign' in msg_lower or 'festival' in msg_lower:
                ai_response = f"""
**🎉 Campaign Generation**

I can help you create a complete campaign! Here's what I recommend:

**For {user_settings.get('business_name', 'your business')}:**

1. **WhatsApp Broadcast** - Direct customer outreach
2. **Social Media Posts** - Instagram, Facebook, Twitter
3. **Email Newsletter** - For your subscriber list
4. **Local Partnerships** - Collaborate with tour operators

**Next Steps:**
- Use **WhatsApp Studio** for broadcast messages
- Use **Content Studio** for social media content
- Use **Lead Finder** to find partnership opportunities

Would you like me to generate any specific campaign material? Just tell me:
- Campaign type (festival, offer, announcement)
- Target audience
- Key message or offer details
"""
            elif 'hotel' in msg_lower or 'lead' in msg_lower or 'find' in msg_lower:
                ai_response = """
**🎯 Lead Generation**

I can help you find potential business partners!

**Best Approach:**
Use the **Lead Finder** module for:
- ✅ Verified business emails
- ✅ Contact person details
- ✅ Company information
- ✅ AI-personalized outreach emails

**Quick Search Parameters:**
- Category: boutique hotels, restaurants, tour operators
- Location: Your target city
- Number of leads: 5-10

**Pro Tip:** After finding leads, use **Response Writer** to create personalized property profiles and outreach emails.

👉 Click **Lead Finder** in the sidebar to start!
"""
            elif 'review' in msg_lower or 'reply' in msg_lower or 'response' in msg_lower:
                ai_response = """
**⭐ Review Response**

I'll help you craft the perfect response to any review!

**What I need from you:**
1. Reviewer's name
2. The review text
3. Sentiment (positive/negative/mixed)

**My responses will:**
- ✅ Match your brand voice
- ✅ Address specific concerns
- ✅ Be empathetic and professional
- ✅ Include your contact info

**Example Response:**
*"Dear [Name], thank you for your feedback! [Specific acknowledgment]. [Action/offer]. We look forward to welcoming you back. Warm regards, [Your Name]"*

 Use **Response Writer** for a guided experience, or paste the review here and I'll draft it now!
"""
            elif 'whatsapp' in msg_lower or 'broadcast' in msg_lower:
                ai_response = f"""
**📱 WhatsApp Broadcast**

Let's create an engaging message for your customers!

**Campaign Elements:**
- Eye-catching emojis (1-2 per line)
- Clear offer or message
- Strong call-to-action
- Unsubscribe option

**Template:**
*"🌟 [Headline] 🌟

[Main message/offer]

✅ [Benefit 1]
✅ [Benefit 2]
✅ [Validity/Deadline]

Reply [ACTION] to [desired action]!

{user_settings.get('business_name', 'Your Business')}
{user_settings.get('contact_info', 'Contact')}

Reply STOP to unsubscribe"*

**Tell me:**
- What's the offer or message?
- Who's the target audience?
- Any specific details to include?

Or click **WhatsApp Studio** for a guided experience!
"""
            else:
                ai_response = f"""
**🤖 ARIA Assistant**

I'm here to help you with your business automation!

**I can assist with:**
- 🎉 **Campaign Generation** - Festival, offers, announcements
-  **Lead Generation** - Find businesses in your area
- ⭐ **Review Responses** - Professional replies to customer reviews
- 📱 **WhatsApp Campaigns** - Engaging broadcast messages
-  **Content Creation** - Blogs, social posts, newsletters
- 🤝 **Vendor Negotiation** - Cost reduction emails

**Quick Actions:**
Use the suggestion buttons above, or tell me what you need!

**Your Business:** {user_settings.get('business_name', 'Not configured')}
**Location:** {user_settings.get('location', 'Not set')}

💡 **Tip:** Complete your **Business Profile** for personalized AI responses!
"""
            
            st.session_state['chat_history'].append({'role': 'assistant', 'content': ai_response})
            st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Clear chat button
    if st.session_state['chat_history']:
        if st.button("🗑️ Clear Chat History", type="secondary"):
            st.session_state['chat_history'] = []
            st.rerun()

# --- COMING SOON PAGES ---
elif page in ['team', 'api', 'manual']:
    titles = {'team': 'Team Members', 'api': 'API Keys', 'manual': 'User Manual'}
    page_header(titles.get(page, "Page"), "This module is coming soon.", f"Home › {titles.get(page, '')}")
    st.markdown('<div class="dashboard-card" style="text-align:center; padding:60px;"><div style="font-size:48px; margin-bottom:16px;">🚧</div><h3 style="color:#0F172A;">Under Construction</h3><p style="color:#64748B;">We are building this feature. Check back soon!</p></div>', unsafe_allow_html=True)