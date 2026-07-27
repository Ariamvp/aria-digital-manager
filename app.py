import os
import json
import re
import logging
import requests
import uuid
from datetime import datetime, timezone
import streamlit as st
from dotenv import load_dotenv
from crewai import Agent, Task, Crew, Process, LLM
from crewai_tools import TavilySearchTool, ScrapeWebsiteTool
from db import supabase, supabase_admin, get_user_settings, save_user_settings, save_approval

# ==========================================
# 1. INITIALIZATION & THEME
# ==========================================
load_dotenv()
st.set_page_config(page_title="A.R.I.A. SaaS", page_icon="🤖", layout="wide")

# Initialize session state
if 'user_type' not in st.session_state:
    st.session_state['user_type'] = "Business Owner"
if 'theme' not in st.session_state:
    st.session_state['theme'] = "Dark Mode"
if 'active_module' not in st.session_state:
    st.session_state['active_module'] = "vendor" # Default module

# Dynamic CSS based on Theme
is_dark = st.session_state['theme'] == "Dark Mode"
bg_color = "#0A1120" if is_dark else "#F8F9FA"
panel_color = "#111A2E" if is_dark else "#FFFFFF"
panel_input = "#0D1626" if is_dark else "#F1F3F5"
line_color = "#223052" if is_dark else "#DEE2E6"
text_color = "#E7ECF6" if is_dark else "#212529"
text_mid = "#9AA6C2" if is_dark else "#495057"

st.markdown(f"""
<style>
    /* Global */
    .stApp {{ background-color: {bg_color}; color: {text_color}; font-family: 'Inter', system-ui, sans-serif; }}
    
    /* Sidebar */
    section[data-testid="stSidebar"] {{ 
        background-color: {panel_color} !important; 
        border-right: 1px solid {line_color}; 
        padding: 20px 15px !important;
    }}
    section[data-testid="stSidebar"] .stMarkdown, section[data-testid="stSidebar"] label {{ color: {text_color} !important; }}
    
    /* FIX: Login/Signup Page Label Visibility */
    .stTextInput label, .stTextArea label, .stSelectbox label, .stRadio label, .stCheckbox label {{
        color: {text_color} !important;
        font-weight: 500 !important;
    }}
    .stTabs [data-baseweb="tab"] {{ color: {text_mid} !important; }}
    .stTabs [aria-selected="true"] {{ color: {text_color} !important; }}
    
    /* Inputs */
    .stTextInput > div > div > input, .stTextArea > div > div > textarea, .stSelectbox > div > div > div {{
        background-color: {panel_input} !important; color: {text_color} !important; 
        border: 1px solid {line_color} !important; border-radius: 8px !important;
    }}
    .stTextInput > div > div > input:focus, .stTextArea > div > div > textarea:focus, .stSelectbox > div > div > div:focus {{
        border-color: #5EEAD4 !important; box-shadow: 0 0 0 1px #5EEAD4 !important;
    }}
    
    /* Buttons */
    .stButton > button[kind="primary"] {{
        background-color: #FFB454 !important; color: #211505 !important; border: 1px solid #FFB454 !important;
        border-radius: 8px !important; font-weight: 600 !important; transition: all 0.15s ease !important;
    }}
    .stButton > button[kind="primary"]:hover {{ background-color: #FFC578 !important; transform: translateY(-1px) !important; }}
    
    .stButton > button[kind="secondary"] {{
        background-color: transparent !important; color: {text_color} !important; border: 1px solid {line_color} !important;
        border-radius: 8px !important; font-weight: 500 !important; transition: all 0.15s ease !important;
    }}
    .stButton > button[kind="secondary"]:hover {{ border-color: #5C6785 !important; background-color: {panel_input} !important; }}

    /* Code Blocks */
    .stCodeBlock {{ background-color: {panel_input} !important; border: 1px solid {line_color} !important; border-radius: 8px !important; }}
    
    /* Hide Streamlit Branding */
    #MainMenu {{visibility: hidden;}} footer {{visibility: hidden;}} header {{visibility: hidden;}}
    .stMarkdown p, .stMarkdown li, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {{ color: {text_color}; }}
    
    /* Custom Sidebar Section Headers */
    .sidebar-header {{ font-size: 11px; text-transform: uppercase; letter-spacing: 1px; color: {text_mid}; margin-bottom: 10px; margin-top: 20px; }}
</style>
""", unsafe_allow_html=True)

# Helper: Quick Copy Button
def add_quick_copy(text):
    safe_text = text.replace("\\", "\\\\").replace("'", "\\'").replace("`", "\\`").replace("\n", "\\n").replace("\r", "")
    btn_id = f"btn_{uuid.uuid4().hex[:8]}"
    st.markdown(
        f"""
        <button id="{btn_id}" style="background-color: {panel_input}; border: 1px solid {line_color}; color: {text_color}; padding: 6px 12px; border-radius: 5px; cursor: pointer; font-size: 13px; margin-bottom: 10px;">
            📋 Copy to Clipboard
        </button>
        <script>
            document.getElementById("{btn_id}").onclick = function() {{
                navigator.clipboard.writeText('{safe_text}');
                this.innerHTML = "✅ Copied!";
                this.style.backgroundColor = "#d4edda";
                this.style.color = "#155724";
                setTimeout(() => {{ this.innerHTML = "📋 Copy to Clipboard"; this.style.backgroundColor = "{panel_input}"; this.style.color = "{text_color}"; }}, 2000);
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
# 3. CREW DEFINITIONS
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
        Task(description='Output strict JSON: {{"subject": "...", "body": "..."}}', expected_output="JSON", agent=qa)
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
        Task(description='Format ALL into JSON: {{"blog": "...", "linkedin": "...", "twitter": "...", "instagram": "...", "newsletter": "..."}}', expected_output="JSON", agent=qa)
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
        ## 📍 Location, 🛏️ Rooms, 💰 Rates, 🍽️ Meals, ✨ Amenities, 📸 Photos, 🌟 Offers, 🗺️ Nearby (Extract from details)
        
        === PART 2: EMAIL ===
        Write short email (<100 words):
        1. Extract sender name. If blank, use "Valued Partner".
        2. Start "Dear [Name],"
        3. Thank them for interest in {business_name}.
        4. Say "Please find our detailed Property Profile above."
        5. Sign off professionally using exactly this contact info: {contact_info}
        
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
# 4. USER MANUAL DIALOG
# ==========================================
@st.dialog("📖 A.R.I.A. User Manual")
def show_user_manual():
    st.markdown("""
    **Welcome to A.R.I.A.!** Here is how to get the most out of your AI workforce:
    
    ### 🚀 Getting Started
    1. **Business Owners:** Fill out **⚙️ Business Settings** first - A.R.I.A. uses this to personalize all outputs.
    2. **Educational Users:** You can skip settings and test all modules freely with dummy data!
    
    ### 🧠 How to Use Each Module
    - **🎯 Local Lead Gen:** Find real businesses in your target area. The AI researches and drafts personalized emails.
    - **📩 Lead Response:** When clients reply to you, paste their inquiry here. A.R.I.A. generates a property profile and professional reply.
    - **⭐ Review Responses:** Paste any review (positive or negative). A.R.I.A. drafts an empathetic, brand-safe response.
    - **🔄 Content Repurposing:** Feed it one piece of content. Get a full week of marketing materials.
    - **🤝 Vendor Negotiation:** Lower your business costs. AI researches competitors and drafts negotiation emails.
    - **📱 WhatsApp Broadcasts:** Create engaging broadcasts with emojis and CTAs for your customer list.
    
    ### 🔐 Approvals
    If you connect Telegram, A.R.I.A. will send drafts to your phone. Reply to approve before anything sends.
    
    **Your 14-day trial includes full access to all 6 modules!**
    """)
    if st.button("Close Manual", use_container_width=True):
        st.rerun()

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

# --- SIDEBAR (LEFT PANEL) ---
with st.sidebar:
    st.header("🤖 A.R.I.A.")
    st.subheader(f"👤 {st.session_state['user'].email}")
    
    if user_role == 'admin':
        st.markdown("🔴 **ADMIN** · Unlimited Access")
    else:
        st.markdown("**14-Day Free Trial Active**")
    
    st.divider()
    
    # Navigation Menu
    st.markdown('<div class="sidebar-header">🧭 Modules</div>', unsafe_allow_html=True)
    
    # Business Settings (Only for Business Owners)
    if st.session_state['user_type'] == "Business Owner":
        if st.button("⚙️ Business Settings", use_container_width=True, 
                     type="primary" if st.session_state['active_module'] == 'settings' else "secondary"):
            st.session_state['active_module'] = 'settings'
            st.rerun() # CRITICAL FIX: Forces immediate UI update
            
    if st.button("🤝 Vendor Negotiation", use_container_width=True, 
                 type="primary" if st.session_state['active_module'] == 'vendor' else "secondary"):
        st.session_state['active_module'] = 'vendor'
        st.rerun()
        
    if st.button("🔄 Content Repurposing", use_container_width=True, 
                 type="primary" if st.session_state['active_module'] == 'content' else "secondary"):
        st.session_state['active_module'] = 'content'
        st.rerun()
        
    if st.button("🎯 Local Lead Gen", use_container_width=True, 
                 type="primary" if st.session_state['active_module'] == 'leadgen' else "secondary"):
        st.session_state['active_module'] = 'leadgen'
        st.rerun()
        
    if st.button("📩 Lead Response", use_container_width=True, 
                 type="primary" if st.session_state['active_module'] == 'response' else "secondary"):
        st.session_state['active_module'] = 'response'
        st.rerun()
        
    if st.button("⭐ Review Responses", use_container_width=True, 
                 type="primary" if st.session_state['active_module'] == 'review' else "secondary"):
        st.session_state['active_module'] = 'review'
        st.rerun()
        
    if st.button("📱 WhatsApp Broadcasts", use_container_width=True, 
                 type="primary" if st.session_state['active_module'] == 'whatsapp' else "secondary"):
        st.session_state['active_module'] = 'whatsapp'
        st.rerun()

    st.divider()
    
    # Preferences Section
    st.markdown('<div class="sidebar-header">⚙️ Preferences</div>', unsafe_allow_html=True)
    
    new_user_type = st.selectbox(
        "Account Type",
        options=["Business Owner", "Educational User / Other"],
        index=0 if st.session_state['user_type'] == "Business Owner" else 1,
        help="Educational users can test modules freely without configuring business settings."
    )
    if new_user_type != st.session_state['user_type']:
        st.session_state['user_type'] = new_user_type
        if new_user_type == "Educational User / Other" and st.session_state['active_module'] == 'settings':
            st.session_state['active_module'] = 'vendor' # Reset to default if settings is hidden
        st.rerun()
        
    new_theme = st.selectbox(
        "Theme",
        options=["Dark Mode", "Light Mode"],
        index=0 if st.session_state['theme'] == "Dark Mode" else 1
    )
    if new_theme != st.session_state['theme']:
        st.session_state['theme'] = new_theme
        st.rerun()
        
    if st.button("📖 Open User Manual", use_container_width=True, type="secondary"):
        show_user_manual()
        
    st.divider()
    
    if st.button("🚪 Logout", use_container_width=True, type="secondary"):
        supabase.auth.sign_out()
        st.session_state.clear()
        st.rerun()

# --- MAIN AREA (RIGHT PANEL) ---
active = st.session_state['active_module']

# 1. BUSINESS SETTINGS
if active == 'settings' and st.session_state['user_type'] == "Business Owner":
    st.header("⚙️ Configure Your Business Profile")
    st.markdown("A.R.I.A. uses these details to personalize all outputs.")
    with st.form("settings_form"):
        col1, col2 = st.columns(2)
        with col1:
            biz_name = st.text_input("Business Name *", value=user_settings.get('business_name', ''))
            industry = st.selectbox("Industry", ["Hospitality", "Food/FMCG", "Service", "Retail", "Other"], index=0)
            location = st.text_input("Primary Location *", value=user_settings.get('location', ''))
        with col2:
            contact_info = st.text_input("Contact Info (Name | Phone | Email) *", value=user_settings.get('contact_info', ''))
            biz_pitch = st.text_area("Core Pitch *", height=100, value=user_settings.get('business_pitch', ''))
            
        st.subheader("🔐 Integration Credentials")
        col3, col4 = st.columns(2)
        with col3:
            gmail_pw = st.text_input("Gmail App Password", type="password", value=user_settings.get('gmail_app_password', ''))
            tg_token = st.text_input("Telegram Bot Token", type="password", value=user_settings.get('telegram_bot_token', ''))
        with col4:
            tg_chat = st.text_input("Telegram Chat ID", value=user_settings.get('telegram_chat_id', ''))

        if st.form_submit_button("💾 Save Settings", type="primary", use_container_width=True):
            save_user_settings(st.session_state['user'].id, {
                "business_name": biz_name, "industry": industry, "location": location,
                "contact_info": contact_info, "business_pitch": biz_pitch,
                "gmail_app_password": gmail_pw, "telegram_bot_token": tg_token,
                "telegram_chat_id": tg_chat
            })
            st.success("✅ Settings saved!")
            st.rerun()

# 2. VENDOR NEGOTIATION
elif active == 'vendor':
    st.header("🤝 Vendor Negotiation")
    if st.session_state['user_type'] == "Educational User / Other":
        st.info("🎓 **Educational Mode:** You can test this module freely!")
    elif not user_settings.get('contact_info'):
        st.warning("⚠️ Complete Business Settings first!")
    else:
        with st.form("negotiation_form"):
            v_name = st.text_input("Vendor Name")
            v_service = st.text_input("Current Service")
            v_cost = st.text_input("Monthly Cost ($)")
            v_date = st.text_input("Contract End Date")
            
            if st.form_submit_button("🚀 Generate", type="primary"):
                with st.spinner("Researching..."):
                    crew = create_negotiation_crew()
                    result = crew.kickoff(inputs={
                        "vendor_name": v_name, "current_service": v_service,
                        "monthly_cost": v_cost, "contract_end_date": v_date,
                        "contact_info": user_settings['contact_info']
                    })
                    parsed = parse_json_output(result.raw)
                    st.success("✅ Draft Generated!")
                    add_quick_copy(parsed.get('body', ''))
                    st.code(parsed.get('body', ''), language="text")

# 3. CONTENT REPURPOSING
elif active == 'content':
    st.header("🔄 Content Repurposing")
    if st.session_state['user_type'] == "Educational User / Other":
        st.info("🎓 **Educational Mode:** Test freely with any content!")
    
    with st.form("repurpose_form"):
        source = st.text_area("Source Material", height=150)
        audience = st.text_input("Target Audience")
        
        if st.form_submit_button("🔄 Repurpose", type="primary"):
            with st.spinner("Analyzing..."):
                crew = create_repurposing_crew()
                result = crew.kickoff(inputs={"source_content": source, "target_audience": audience})
                parsed = parse_json_output(result.raw)
                st.success("✅ Generated!")
                st.subheader("📝 Blog Post")
                add_quick_copy(parsed.get('blog', ''))
                st.markdown(parsed.get('blog', ''))

# 4. LOCAL LEAD GEN
elif active == 'leadgen':
    st.header("🎯 Local Lead Discovery")
    if st.session_state['user_type'] == "Educational User / Other":
        st.info("🎓 **Educational Mode:** Find leads freely!")
    elif not user_settings.get('business_pitch'):
        st.warning("⚠️ Complete Business Settings first!")
    else:
        with st.form("lead_form"):
            category = st.text_input("Target Category", value="tour operators")
            location_search = st.text_input("Location", value=user_settings.get('location', ''))
            num_leads = st.slider("Number of Leads", 3, 10, 5)
            
            if st.form_submit_button("🔍 Find Leads", type="primary"):
                with st.spinner("Searching..."):
                    crew = create_prospect_finder_crew()
                    result = crew.kickoff(inputs={
                        "category": category, "location": location_search, "num_leads": num_leads
                    })
                    st.success("✅ Leads Found!")
                    st.code(result.raw, language="json")

# 5. LEAD RESPONSE
elif active == 'response':
    st.header("📩 Lead Response & Assets")
    if st.session_state['user_type'] == "Educational User / Other":
        st.info("🎓 **Educational Mode:** Test with any lead inquiry!")
    
    with st.form("response_form"):
        incoming = st.text_area("Incoming Lead Request", height=100)
        raw_details = st.text_area("Your Business Details", height=150)
        
        if st.form_submit_button("✨ Generate", type="primary"):
            with st.spinner("Crafting..."):
                crew = create_response_crew()
                result = crew.kickoff(inputs={
                    "incoming_request": incoming, "raw_business_details": raw_details,
                    "business_name": user_settings.get('business_name', 'Your Business'),
                    "contact_info": user_settings.get('contact_info', '')
                })
                st.success("✅ Generated!")
                parts = result.raw.split("---EMAIL---")
                st.subheader("📋 Property Profile")
                add_quick_copy(parts[0])
                st.markdown(parts[0])
                if len(parts) > 1:
                    st.divider()
                    st.subheader("📧 Email Reply")
                    add_quick_copy(parts[1])
                    st.markdown(parts[1])

# 6. REVIEW RESPONSES
elif active == 'review':
    st.header("⭐ Review Response Generator")
    if st.session_state['user_type'] == "Educational User / Other":
        st.info("🎓 **Educational Mode:** Test with any review!")
    
    with st.form("review_form"):
        reviewer = st.text_input("Reviewer Name")
        review_text = st.text_area("Review Text", height=100)
        sentiment = st.radio("Sentiment", ["Positive", "Negative", "Mixed"])
        
        if st.form_submit_button("✨ Generate", type="primary"):
            with st.spinner("Writing..."):
                crew = create_review_crew()
                result = crew.kickoff(inputs={
                    "reviewer_name": reviewer, "review_text": review_text,
                    "sentiment": sentiment, "contact_info": user_settings.get('contact_info', '')
                })
                st.success("✅ Generated!")
                add_quick_copy(result.raw)
                st.markdown(result.raw)

# 7. WHATSAPP BROADCASTS
elif active == 'whatsapp':
    st.header("📱 WhatsApp Broadcast Generator")
    if st.session_state['user_type'] == "Educational User / Other":
        st.info("🎓 **Educational Mode:** Create broadcasts freely!")
    elif not user_settings.get('business_name'):
        st.warning("⚠️ Complete Business Settings first!")
    else:
        with st.form("wa_form"):
            btype = st.selectbox("Type", ["Special Offer", "Festival Greeting", "Welcome Back"])
            details = st.text_area("Offer Details")
            
            if st.form_submit_button("✨ Generate", type="primary"):
                with st.spinner("Creating..."):
                    crew = create_whatsapp_crew()
                    result = crew.kickoff(inputs={
                        "business_name": user_settings['business_name'],
                        "broadcast_type": btype, "specific_details": details,
                        "contact_info": user_settings.get('contact_info', '')
                    })
                    st.success("✅ Generated!")
                    add_quick_copy(result.raw)
                    st.code(result.raw, language="text")