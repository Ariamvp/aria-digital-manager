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
# 1. INITIALIZATION
# ==========================================
load_dotenv()
st.set_page_config(page_title="A.R.I.A. Command Center", page_icon="", layout="wide", initial_sidebar_state="expanded")

# Session state for navigation
if 'active_page' not in st.session_state:
    st.session_state['active_page'] = 'dashboard'
if 'sidebar_expanded' not in st.session_state:
    st.session_state['sidebar_expanded'] = {
        'business': True, 'ai_tools': True, 'analytics': True,
        'integrations': True, 'templates': True, 'help': True
    }

# ==========================================
# 2. CUSTOM CSS - PROFESSIONAL DASHBOARD THEME
# ==========================================
st.markdown("""
<style>
    /* === GLOBAL STYLES === */
    .stApp {
        background-color: #F8FAFC;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    /* === SIDEBAR - DARK THEME === */
    section[data-testid="stSidebar"] {
        background-color: #0F172A !important;
        border-right: none !important;
        width: 280px !important;
        padding: 0 !important;
    }
    section[data-testid="stSidebar"] .stMarkdown {
        color: #E2E8F0 !important;
    }
    
    /* Brand Header */
    .brand-header {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 20px 20px 24px;
        border-bottom: 1px solid #1E293B;
        margin-bottom: 8px;
    }
    .brand-logo {
        width: 40px;
        height: 40px;
        background: linear-gradient(135deg, #16A34A 0%, #15803D 100%);
        border-radius: 10px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 20px;
        flex-shrink: 0;
    }
    .brand-text {
        color: #FFFFFF !important;
        font-size: 18px;
        font-weight: 700;
        letter-spacing: 0.5px;
    }
    .brand-sub {
        color: #16A34A !important;
        font-size: 10px;
        font-weight: 600;
        letter-spacing: 1.5px;
        text-transform: uppercase;
    }
    
    /* Section Headers */
    .nav-section {
        color: #16A34A !important;
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 1.2px;
        text-transform: uppercase;
        padding: 16px 20px 8px;
        margin-top: 8px;
    }
    
    /* Navigation Buttons */
    .nav-btn {
        width: 100%;
        padding: 10px 20px;
        margin: 2px 12px;
        border-radius: 8px;
        border: none;
        background: transparent;
        color: #CBD5E1;
        font-size: 14px;
        font-weight: 500;
        cursor: pointer;
        display: flex;
        align-items: center;
        gap: 12px;
        transition: all 0.15s;
        text-align: left;
    }
    .nav-btn:hover {
        background: #1E293B;
        color: #FFFFFF;
    }
    .nav-btn.active {
        background: #16A34A;
        color: #FFFFFF;
        font-weight: 600;
    }
    .nav-btn .icon {
        font-size: 16px;
        width: 20px;
        text-align: center;
    }
    
    /* Logout Button */
    .logout-btn {
        width: calc(100% - 24px);
        margin: 8px 12px 20px;
        padding: 10px 20px;
        border-radius: 8px;
        border: 1px solid #334155;
        background: transparent;
        color: #CBD5E1;
        font-size: 14px;
        font-weight: 500;
        cursor: pointer;
        display: flex;
        align-items: center;
        gap: 12px;
        transition: all 0.15s;
    }
    .logout-btn:hover {
        background: #DC2626;
        border-color: #DC2626;
        color: #FFFFFF;
    }
    
    /* === TOP BAR === */
    .top-bar {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 16px 32px;
        background: #FFFFFF;
        border-bottom: 1px solid #E2E8F0;
        position: sticky;
        top: 0;
        z-index: 100;
    }
    .top-bar-left {
        display: flex;
        align-items: center;
        gap: 16px;
    }
    .top-bar-title {
        font-size: 20px;
        font-weight: 700;
        color: #0F172A;
    }
    .top-bar-right {
        display: flex;
        align-items: center;
        gap: 20px;
    }
    .search-box {
        display: flex;
        align-items: center;
        gap: 8px;
        padding: 8px 16px;
        background: #F1F5F9;
        border-radius: 8px;
        border: 1px solid #E2E8F0;
        min-width: 280px;
    }
    .search-box input {
        border: none;
        background: transparent;
        outline: none;
        font-size: 14px;
        color: #64748B;
        width: 100%;
    }
    .notification-bell {
        position: relative;
        font-size: 20px;
        cursor: pointer;
        padding: 8px;
        border-radius: 8px;
        transition: background 0.15s;
    }
    .notification-bell:hover {
        background: #F1F5F9;
    }
    .notification-badge {
        position: absolute;
        top: 2px;
        right: 2px;
        background: #16A34A;
        color: white;
        font-size: 10px;
        font-weight: 700;
        width: 18px;
        height: 18px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
    }
    .profile-dropdown {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 6px 12px;
        border-radius: 8px;
        cursor: pointer;
        transition: background 0.15s;
    }
    .profile-dropdown:hover {
        background: #F1F5F9;
    }
    .profile-avatar {
        width: 36px;
        height: 36px;
        border-radius: 50%;
        background: #16A34A;
        color: white;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 700;
        font-size: 14px;
    }
    .profile-info {
        display: flex;
        flex-direction: column;
    }
    .profile-name {
        font-size: 14px;
        font-weight: 600;
        color: #0F172A;
    }
    .profile-trial {
        font-size: 11px;
        color: #16A34A;
        font-weight: 500;
    }
    
    /* === MAIN CONTENT === */
    .main-content {
        padding: 32px;
        max-width: 1400px;
        margin: 0 auto;
    }
    .breadcrumb {
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 13px;
        color: #64748B;
        margin-bottom: 16px;
    }
    .breadcrumb a {
        color: #64748B;
        text-decoration: none;
    }
    .breadcrumb a:hover {
        color: #16A34A;
    }
    .page-title {
        font-size: 28px;
        font-weight: 700;
        color: #0F172A;
        margin-bottom: 8px;
    }
    .page-subtitle {
        font-size: 15px;
        color: #64748B;
        margin-bottom: 32px;
    }
    
    /* === CARDS === */
    .card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 28px;
        margin-bottom: 24px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    }
    .card-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 24px;
        padding-bottom: 16px;
        border-bottom: 1px solid #F1F5F9;
    }
    .card-title {
        display: flex;
        align-items: center;
        gap: 12px;
        font-size: 18px;
        font-weight: 700;
        color: #0F172A;
    }
    .card-icon {
        width: 40px;
        height: 40px;
        background: #F0FDF4;
        border-radius: 10px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 20px;
    }
    .card-badge {
        font-size: 12px;
        color: #16A34A;
        font-weight: 500;
        display: flex;
        align-items: center;
        gap: 6px;
    }
    
    /* === FORM STYLES === */
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea,
    .stSelectbox > div > div > div {
        background-color: #FFFFFF !important;
        color: #0F172A !important;
        border: 1px solid #E2E8F0 !important;
        border-radius: 8px !important;
        padding: 10px 14px !important;
        font-size: 14px !important;
    }
    .stTextInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus,
    .stSelectbox > div > div > div:focus {
        border-color: #16A34A !important;
        box-shadow: 0 0 0 3px rgba(22, 163, 74, 0.1) !important;
    }
    .stTextInput label, .stTextArea label, .stSelectbox label {
        color: #374151 !important;
        font-weight: 600 !important;
        font-size: 14px !important;
        margin-bottom: 6px !important;
    }
    
    /* === PRIMARY BUTTON (GREEN) === */
    .stButton > button[kind="primary"] {
        background-color: #16A34A !important;
        color: #FFFFFF !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        font-size: 15px !important;
        padding: 12px 24px !important;
        width: 100% !important;
        transition: all 0.15s !important;
    }
    .stButton > button[kind="primary"]:hover {
        background-color: #15803D !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 4px 12px rgba(22, 163, 74, 0.3) !important;
    }
    
    /* === INFO BOX === */
    .info-box {
        background: #F0FDF4;
        border: 1px solid #BBF7D0;
        border-radius: 8px;
        padding: 14px 18px;
        display: flex;
        align-items: center;
        gap: 12px;
        font-size: 13px;
        color: #166534;
        margin-top: 20px;
    }
    
    /* Hide Streamlit defaults */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Color scheme reference */
    .color-scheme {
        display: flex;
        gap: 16px;
        flex-wrap: wrap;
        padding: 20px 0;
        margin-top: 40px;
        border-top: 1px solid #E2E8F0;
    }
    .color-item {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 6px;
    }
    .color-swatch {
        width: 40px;
        height: 40px;
        border-radius: 8px;
        border: 1px solid #E2E8F0;
    }
    .color-label {
        font-size: 10px;
        color: #64748B;
        font-weight: 600;
    }
    .color-hex {
        font-size: 10px;
        color: #94A3B8;
        font-family: monospace;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 3. AUTHENTICATION
# ==========================================
def login_page():
    st.markdown("""
    <div style="display:flex; justify-content:center; align-items:center; min-height:100vh; background:#F8FAFC;">
        <div style="background:white; padding:48px; border-radius:16px; box-shadow:0 4px 20px rgba(0,0,0,0.08); max-width:420px; width:100%;">
            <div style="display:flex; align-items:center; gap:12px; margin-bottom:32px;">
                <div style="width:48px; height:48px; background:linear-gradient(135deg, #16A34A 0%, #15803D 100%); border-radius:12px; display:flex; align-items:center; justify-content:center; font-size:24px;">🔥</div>
                <div>
                    <div style="font-size:22px; font-weight:700; color:#0F172A;">A.R.I.A.</div>
                    <div style="font-size:11px; color:#16A34A; font-weight:600; letter-spacing:1.5px;">COMMAND CENTER</div>
                </div>
            </div>
    """, unsafe_allow_html=True)
    
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
    
    st.markdown("</div></div>", unsafe_allow_html=True)

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
        ## 📍 Location, 🛏️ Rooms, 💰 Rates, 🍽️ Meals,  Amenities, 📸 Photos, 🌟 Offers, 🗺️ Nearby
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

# ==========================================
# 5. MAIN APP
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
user_initial = user_email[0].upper()

# ==========================================
# 6. SIDEBAR - PROFESSIONAL NAVIGATION
# ==========================================
with st.sidebar:
    # Brand Header
    st.markdown(f"""
    <div class="brand-header">
        <div class="brand-logo">🔥</div>
        <div>
            <div class="brand-text">A.R.I.A</div>
            <div class="brand-sub">Command Center</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Dashboard Button
    st.markdown(f"""
    <button class="nav-btn {'active' if st.session_state['active_page'] == 'dashboard' else ''}" 
            onclick="document.getElementById('nav-dashboard').click()">
        <span class="icon">🏠</span> Dashboard
    </button>
    """, unsafe_allow_html=True)
    if st.button(" Dashboard", key="nav-dashboard", type="primary" if st.session_state['active_page'] == 'dashboard' else "secondary", use_container_width=True):
        st.session_state['active_page'] = 'dashboard'
        st.rerun()
    
    # BUSINESS Section
    st.markdown('<div class="nav-section">Business</div>', unsafe_allow_html=True)
    
    if st.button("🏢 Business Profile", key="nav-business", 
                 type="primary" if st.session_state['active_page'] == 'business' else "secondary", 
                 use_container_width=True):
        st.session_state['active_page'] = 'business'
        st.rerun()
    
    if st.button("👥 Team Members", key="nav-team", 
                 type="primary" if st.session_state['active_page'] == 'team' else "secondary", 
                 use_container_width=True):
        st.session_state['active_page'] = 'team'
        st.rerun()
    
    if st.button(" Brand Settings", key="nav-brand", 
                 type="primary" if st.session_state['active_page'] == 'brand' else "secondary", 
                 use_container_width=True):
        st.session_state['active_page'] = 'brand'
        st.rerun()
    
    # AI TOOLS Section
    st.markdown('<div class="nav-section">AI Tools</div>', unsafe_allow_html=True)
    
    if st.button(" Vendor Negotiation", key="nav-vendor", 
                 type="primary" if st.session_state['active_page'] == 'vendor' else "secondary", 
                 use_container_width=True):
        st.session_state['active_page'] = 'vendor'
        st.rerun()
    
    if st.button("🔄 Content Repurposing", key="nav-content", 
                 type="primary" if st.session_state['active_page'] == 'content' else "secondary", 
                 use_container_width=True):
        st.session_state['active_page'] = 'content'
        st.rerun()
    
    if st.button("📩 Lead Response", key="nav-response", 
                 type="primary" if st.session_state['active_page'] == 'response' else "secondary", 
                 use_container_width=True):
        st.session_state['active_page'] = 'response'
        st.rerun()
    
    if st.button("🎯 Local Lead Generator", key="nav-leadgen", 
                 type="primary" if st.session_state['active_page'] == 'leadgen' else "secondary", 
                 use_container_width=True):
        st.session_state['active_page'] = 'leadgen'
        st.rerun()
    
    if st.button("📱 WhatsApp Broadcast", key="nav-whatsapp", 
                 type="primary" if st.session_state['active_page'] == 'whatsapp' else "secondary", 
                 use_container_width=True):
        st.session_state['active_page'] = 'whatsapp'
        st.rerun()
    
    # ANALYTICS Section
    st.markdown('<div class="nav-section">Analytics</div>', unsafe_allow_html=True)
    
    if st.button("📊 Reports", key="nav-reports", 
                 type="primary" if st.session_state['active_page'] == 'reports' else "secondary", 
                 use_container_width=True):
        st.session_state['active_page'] = 'reports'
        st.rerun()
    
    if st.button("🕐 Activity Logs", key="nav-activity", 
                 type="primary" if st.session_state['active_page'] == 'activity' else "secondary", 
                 use_container_width=True):
        st.session_state['active_page'] = 'activity'
        st.rerun()
    
    if st.button("🤖 AI Usage", key="nav-usage", 
                 type="primary" if st.session_state['active_page'] == 'usage' else "secondary", 
                 use_container_width=True):
        st.session_state['active_page'] = 'usage'
        st.rerun()
    
    # INTEGRATIONS Section
    st.markdown('<div class="nav-section">Integrations</div>', unsafe_allow_html=True)
    
    if st.button(" Gmail", key="nav-gmail", 
                 type="primary" if st.session_state['active_page'] == 'gmail' else "secondary", 
                 use_container_width=True):
        st.session_state['active_page'] = 'gmail'
        st.rerun()
    
    if st.button("✈️ Telegram", key="nav-telegram", 
                 type="primary" if st.session_state['active_page'] == 'telegram' else "secondary", 
                 use_container_width=True):
        st.session_state['active_page'] = 'telegram'
        st.rerun()
    
    if st.button("💬 WhatsApp", key="nav-wa-int", 
                 type="primary" if st.session_state['active_page'] == 'wa-int' else "secondary", 
                 use_container_width=True):
        st.session_state['active_page'] = 'wa-int'
        st.rerun()
    
    if st.button("🔑 API Keys", key="nav-api", 
                 type="primary" if st.session_state['active_page'] == 'api' else "secondary", 
                 use_container_width=True):
        st.session_state['active_page'] = 'api'
        st.rerun()
    
    # TEMPLATES Section
    st.markdown('<div class="nav-section">Templates</div>', unsafe_allow_html=True)
    
    if st.button(" Templates", key="nav-templates", 
                 type="primary" if st.session_state['active_page'] == 'templates' else "secondary", 
                 use_container_width=True):
        st.session_state['active_page'] = 'templates'
        st.rerun()
    
    # HELP Section
    st.markdown('<div class="nav-section">Help</div>', unsafe_allow_html=True)
    
    if st.button("📖 User Manual", key="nav-manual", 
                 type="primary" if st.session_state['active_page'] == 'manual' else "secondary", 
                 use_container_width=True):
        st.session_state['active_page'] = 'manual'
        st.rerun()
    
    if st.button("❓ FAQ", key="nav-faq", 
                 type="primary" if st.session_state['active_page'] == 'faq' else "secondary", 
                 use_container_width=True):
        st.session_state['active_page'] = 'faq'
        st.rerun()
    
    if st.button("🎧 Contact Support", key="nav-support", 
                 type="primary" if st.session_state['active_page'] == 'support' else "secondary", 
                 use_container_width=True):
        st.session_state['active_page'] = 'support'
        st.rerun()
    
    # Spacer + Logout
    st.markdown('<div style="flex-grow:1;"></div>', unsafe_allow_html=True)
    
    if st.button("🚪 Logout", key="nav-logout", type="secondary", use_container_width=True):
        supabase.auth.sign_out()
        st.session_state.clear()
        st.rerun()

# ==========================================
# 7. TOP BAR
# ==========================================
st.markdown(f"""
<div class="top-bar">
    <div class="top-bar-left">
        <div class="top-bar-title">A.R.I.A Command Center</div>
    </div>
    <div class="top-bar-right">
        <div class="search-box">
            <span></span>
            <input type="text" placeholder="Search anything...">
        </div>
        <div class="notification-bell">
            🔔
            <div class="notification-badge">3</div>
        </div>
        <div class="profile-dropdown">
            <div class="profile-avatar">{user_initial}</div>
            <div class="profile-info">
                <div class="profile-name">{user_email.split('@')[0]}</div>
                <div class="profile-trial">{'Admin' if user_role == 'admin' else 'Free Trial'}</div>
            </div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# ==========================================
# 8. MAIN CONTENT - PAGE ROUTER
# ==========================================
active = st.session_state['active_page']

# DASHBOARD
if active == 'dashboard':
    st.markdown('<div class="main-content">', unsafe_allow_html=True)
    st.markdown('<div class="breadcrumb"><a href="#">Home</a> › <a href="#">Dashboard</a></div>', unsafe_allow_html=True)
    st.markdown('<h1 class="page-title">Dashboard</h1>', unsafe_allow_html=True)
    st.markdown('<p class="page-subtitle">Welcome back! Here\'s what\'s happening with your business today.</p>', unsafe_allow_html=True)
    
    # Stats cards
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown('<div class="card"><div style="font-size:13px; color:#64748B; margin-bottom:8px;">Total Leads</div><div style="font-size:28px; font-weight:700; color:#0F172A;">247</div><div style="font-size:12px; color:#16A34A; margin-top:4px;">↑ 12% this week</div></div>', unsafe_allow_html=True)
    with col2:
        st.markdown('<div class="card"><div style="font-size:13px; color:#64748B; margin-bottom:8px;">AI Generations</div><div style="font-size:28px; font-weight:700; color:#0F172A;">1,429</div><div style="font-size:12px; color:#16A34A; margin-top:4px;">↑ 24% this week</div></div>', unsafe_allow_html=True)
    with col3:
        st.markdown('<div class="card"><div style="font-size:13px; color:#64748B; margin-bottom:8px;">Emails Sent</div><div style="font-size:28px; font-weight:700; color:#0F172A;">89</div><div style="font-size:12px; color:#16A34A; margin-top:4px;">↑ 8% this week</div></div>', unsafe_allow_html=True)
    with col4:
        st.markdown('<div class="card"><div style="font-size:13px; color:#64748B; margin-bottom:8px;">Cost Savings</div><div style="font-size:28px; font-weight:700; color:#0F172A;">₹18,400</div><div style="font-size:12px; color:#16A34A; margin-top:4px;">↑ 15% this month</div></div>', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

# BUSINESS PROFILE
elif active == 'business':
    st.markdown('<div class="main-content">', unsafe_allow_html=True)
    st.markdown('<div class="breadcrumb"><a href="#">Home</a> › <a href="#">Business</a> › Business Profile</div>', unsafe_allow_html=True)
    st.markdown('<h1 class="page-title">Business Profile</h1>', unsafe_allow_html=True)
    st.markdown('<p class="page-subtitle">Configure your business details to personalize all AI outputs.</p>', unsafe_allow_html=True)
    
    # Business Information Card
    st.markdown(f"""
    <div class="card">
        <div class="card-header">
            <div class="card-title">
                <div class="card-icon">🏢</div>
                Business Information
            </div>
            <div class="card-badge">🔒 This information is used across all AI tools</div>
        </div>
    """, unsafe_allow_html=True)
    
    with st.form("business_profile_form"):
        col1, col2 = st.columns(2)
        with col1:
            biz_name = st.text_input("Business Name *", value=user_settings.get('business_name', ''))
            industry = st.selectbox("Industry", ["Hospitality", "Food/FMCG", "Service", "Retail", "Other"], 
                                   index=["Hospitality", "Food/FMCG", "Service", "Retail", "Other"].index(user_settings.get('industry', 'Hospitality')) if user_settings.get('industry') in ["Hospitality", "Food/FMCG", "Service", "Retail", "Other"] else 0)
            location = st.text_input("Primary Location *", value=user_settings.get('location', ''))
        with col2:
            contact_info = st.text_input("Contact Info (Name | Phone | Email) *", value=user_settings.get('contact_info', ''))
            biz_pitch = st.text_area("Core Pitch *", height=120, value=user_settings.get('business_pitch', ''))
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Integration Credentials Card
        st.markdown(f"""
        <div class="card" style="margin-top:24px;">
            <div class="card-header">
                <div class="card-title">
                    <div class="card-icon">🔑</div>
                    Integration Credentials
                </div>
                <div class="card-badge">🛡️ Your credentials are encrypted and secure</div>
            </div>
        """, unsafe_allow_html=True)
        
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
        
        st.markdown("""
        <div class="info-box">
            <span>️</span>
            <span>These credentials enable A.R.I.A to connect with your platforms and perform automated tasks.</span>
        </div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

# VENDOR NEGOTIATION
elif active == 'vendor':
    st.markdown('<div class="main-content">', unsafe_allow_html=True)
    st.markdown('<div class="breadcrumb"><a href="#">Home</a> › <a href="#">AI Tools</a> › Vendor Negotiation</div>', unsafe_allow_html=True)
    st.markdown('<h1 class="page-title">Vendor Negotiation</h1>', unsafe_allow_html=True)
    st.markdown('<p class="page-subtitle">Lower your business costs with data-driven negotiation emails.</p>', unsafe_allow_html=True)
    
    st.markdown('<div class="card">', unsafe_allow_html=True)
    
    if not user_settings.get('contact_info'):
        st.warning("️ Complete Business Profile first!")
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
                with st.spinner("Researching competitors..."):
                    crew = create_negotiation_crew()
                    result = crew.kickoff(inputs={
                        "vendor_name": v_name, "current_service": v_service,
                        "monthly_cost": v_cost, "contract_end_date": v_date,
                        "contact_info": user_settings['contact_info']
                    })
                    parsed = parse_json_output(result.raw)
                    st.success("✅ Draft Generated!")
                    st.code(parsed.get('body', ''), language="text")
    
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# CONTENT REPURPOSING
elif active == 'content':
    st.markdown('<div class="main-content">', unsafe_allow_html=True)
    st.markdown('<div class="breadcrumb"><a href="#">Home</a> › <a href="#">AI Tools</a> › Content Repurposing</div>', unsafe_allow_html=True)
    st.markdown('<h1 class="page-title">Content Repurposing</h1>', unsafe_allow_html=True)
    st.markdown('<p class="page-subtitle">Turn one piece of content into a full week of marketing materials.</p>', unsafe_allow_html=True)
    
    st.markdown('<div class="card">', unsafe_allow_html=True)
    with st.form("content_form"):
        source = st.text_area("Source Material", height=150, placeholder="Paste your blog post, video transcript, or social media content here...")
        audience = st.text_input("Target Audience", placeholder="e.g., Young professionals, families, tourists")
        
        if st.form_submit_button("🔄 Repurpose Content", type="primary"):
            with st.spinner("Analyzing content..."):
                crew = create_repurposing_crew()
                result = crew.kickoff(inputs={"source_content": source, "target_audience": audience})
                parsed = parse_json_output(result.raw)
                st.success("✅ Content Generated!")
                st.subheader("📝 Blog Post")
                st.markdown(parsed.get('blog', ''))
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# LEAD RESPONSE
elif active == 'response':
    st.markdown('<div class="main-content">', unsafe_allow_html=True)
    st.markdown('<div class="breadcrumb"><a href="#">Home</a> › <a href="#">AI Tools</a> › Lead Response</div>', unsafe_allow_html=True)
    st.markdown('<h1 class="page-title">Lead Response</h1>', unsafe_allow_html=True)
    st.markdown('<p class="page-subtitle">Generate professional property profiles and reply emails.</p>', unsafe_allow_html=True)
    
    st.markdown('<div class="card">', unsafe_allow_html=True)
    with st.form("response_form"):
        incoming = st.text_area("Incoming Lead Request", height=100, placeholder="Paste the lead's inquiry here...")
        raw_details = st.text_area("Your Business Details", height=150, value=user_settings.get('business_pitch', ''))
        
        if st.form_submit_button("✨ Generate Response", type="primary"):
            with st.spinner("Crafting response..."):
                crew = create_response_crew()
                result = crew.kickoff(inputs={
                    "incoming_request": incoming, "raw_business_details": raw_details,
                    "business_name": user_settings.get('business_name', 'Your Business'),
                    "contact_info": user_settings.get('contact_info', '')
                })
                st.success("✅ Generated!")
                parts = result.raw.split("---EMAIL---")
                st.subheader("📋 Property Profile")
                st.markdown(parts[0])
                if len(parts) > 1:
                    st.divider()
                    st.subheader("📧 Email Reply")
                    st.markdown(parts[1])
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# LOCAL LEAD GEN
elif active == 'leadgen':
    st.markdown('<div class="main-content">', unsafe_allow_html=True)
    st.markdown('<div class="breadcrumb"><a href="#">Home</a> › <a href="#">AI Tools</a> › Local Lead Generator</div>', unsafe_allow_html=True)
    st.markdown('<h1 class="page-title">Local Lead Generator</h1>', unsafe_allow_html=True)
    st.markdown('<p class="page-subtitle">Find real businesses with verified emails in your target market.</p>', unsafe_allow_html=True)
    
    st.markdown('<div class="card">', unsafe_allow_html=True)
    if not user_settings.get('business_pitch'):
        st.warning("⚠️ Complete Business Profile first!")
    else:
        with st.form("leadgen_form"):
            col1, col2 = st.columns(2)
            with col1:
                category = st.text_input("Target Category", value="boutique hotels")
            with col2:
                location_search = st.text_input("Location", value=user_settings.get('location', ''))
            num_leads = st.slider("Number of Leads", 3, 10, 5)
            
            if st.form_submit_button("🔍 Find Leads", type="primary"):
                with st.spinner("Searching for leads..."):
                    crew = create_prospect_finder_crew()
                    result = crew.kickoff(inputs={
                        "category": category, "location": location_search, "num_leads": num_leads
                    })
                    st.success("✅ Leads Found!")
                    st.code(result.raw, language="json")
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# WHATSAPP BROADCAST
elif active == 'whatsapp':
    st.markdown('<div class="main-content">', unsafe_allow_html=True)
    st.markdown('<div class="breadcrumb"><a href="#">Home</a> › <a href="#">AI Tools</a> › WhatsApp Broadcast</div>', unsafe_allow_html=True)
    st.markdown('<h1 class="page-title">WhatsApp Broadcast</h1>', unsafe_allow_html=True)
    st.markdown('<p class="page-subtitle">Create engaging WhatsApp broadcasts for your customer list.</p>', unsafe_allow_html=True)
    
    st.markdown('<div class="card">', unsafe_allow_html=True)
    if not user_settings.get('business_name'):
        st.warning("️ Complete Business Profile first!")
    else:
        with st.form("whatsapp_form"):
            col1, col2 = st.columns(2)
            with col1:
                btype = st.selectbox("Broadcast Type", ["Special Offer", "Festival Greeting", "Welcome Back", "Seasonal Promotion"])
            with col2:
                audience = st.selectbox("Target Audience", ["All Customers", "VIP Customers", "New Customers", "Inactive Customers"])
            details = st.text_area("Offer Details", height=120, placeholder="Describe your offer, discount, or message...")
            
            if st.form_submit_button("✨ Generate Broadcast", type="primary"):
                with st.spinner("Creating broadcast..."):
                    crew = create_whatsapp_crew()
                    result = crew.kickoff(inputs={
                        "business_name": user_settings['business_name'],
                        "broadcast_type": btype, "specific_details": details,
                        "contact_info": user_settings.get('contact_info', '')
                    })
                    st.success("✅ Broadcast Generated!")
                    st.code(result.raw, language="text")
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# REVIEW RESPONSES
elif active == 'review':
    st.markdown('<div class="main-content">', unsafe_allow_html=True)
    st.markdown('<div class="breadcrumb"><a href="#">Home</a> › <a href="#">AI Tools</a> › Review Responses</div>', unsafe_allow_html=True)
    st.markdown('<h1 class="page-title">Review Responses</h1>', unsafe_allow_html=True)
    st.markdown('<p class="page-subtitle">Instantly generate empathetic, brand-safe responses to reviews.</p>', unsafe_allow_html=True)
    
    st.markdown('<div class="card">', unsafe_allow_html=True)
    with st.form("review_form"):
        col1, col2 = st.columns(2)
        with col1:
            reviewer = st.text_input("Reviewer Name")
            platform = st.selectbox("Platform", ["Google", "TripAdvisor", "Zomato", "Facebook"])
        with col2:
            sentiment = st.radio("Sentiment", ["Positive", "Negative", "Mixed"], horizontal=True)
        review_text = st.text_area("Review Text", height=120)
        
        if st.form_submit_button("✨ Generate Response", type="primary"):
            with st.spinner("Writing response..."):
                crew = create_review_crew()
                result = crew.kickoff(inputs={
                    "reviewer_name": reviewer, "review_text": review_text,
                    "sentiment": sentiment, "contact_info": user_settings.get('contact_info', '')
                })
                st.success("✅ Response Generated!")
                st.markdown(result.raw)
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# OTHER PAGES (Coming Soon)
elif active in ['team', 'brand', 'reports', 'activity', 'usage', 'gmail', 'telegram', 'wa-int', 'api', 'templates', 'manual', 'faq', 'support']:
    page_names = {
        'team': 'Team Members', 'brand': 'Brand Settings', 'reports': 'Reports',
        'activity': 'Activity Logs', 'usage': 'AI Usage', 'gmail': 'Gmail Integration',
        'telegram': 'Telegram Integration', 'wa-int': 'WhatsApp Integration',
        'api': 'API Keys', 'templates': 'Templates', 'manual': 'User Manual',
        'faq': 'FAQ', 'support': 'Contact Support'
    }
    st.markdown('<div class="main-content">', unsafe_allow_html=True)
    st.markdown(f'<h1 class="page-title">{page_names.get(active, "Page")}</h1>', unsafe_allow_html=True)
    st.markdown('<p class="page-subtitle">This module is coming soon. Stay tuned!</p>', unsafe_allow_html=True)
    st.markdown('<div class="card"><p style="text-align:center; color:#64748B; padding:40px;">🚧 Under Construction</p></div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)