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
st.set_page_config(page_title="A.R.I.A. Dashboard", page_icon="🔥", layout="wide")

# ==========================================
# 2. CUSTOM CSS
# ==========================================
st.markdown("""
<style>
    .stApp { background-color: #F8FAFC; font-family: 'Inter', -apple-system, sans-serif; }
    
    /* Hide Streamlit defaults */
    #MainMenu {visibility: hidden;} 
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Tabs styling */
    .stTabs [data-baseweb="tab-list"] { 
        gap: 8px; 
        background-color: transparent;
        padding: 0;
    }
    .stTabs [data-baseweb="tab"] { 
        background-color: white;
        border-radius: 8px;
        padding: 12px 24px;
        font-weight: 600;
        color: #64748B;
        border: 1px solid #E2E8F0;
    }
    .stTabs [aria-selected="true"] { 
        background-color: #16A34A;
        color: white;
        border-color: #16A34A;
    }
    
    /* Cards */
    .dashboard-card {
        background: white;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 28px;
        margin-bottom: 24px;
    }
    
    /* Buttons */
    .stButton > button[kind="primary"] {
        background-color: #16A34A !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
    }
    
    /* Metrics */
    .metric-card {
        background: white;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 24px;
    }
    .metric-label { font-size: 13px; color: #64748B; margin-bottom: 8px; }
    .metric-value { font-size: 32px; font-weight: 700; color: #0F172A; }
    .metric-trend { font-size: 12px; color: #16A34A; margin-top: 4px; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 3. AUTHENTICATION
# ==========================================
def login_page():
    st.title("🔥 Welcome to A.R.I.A.")
    st.markdown("Your Autonomous Revenue & Intelligence Agent.")
    
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

# Top bar with user info and logout
col1, col2 = st.columns([6, 1])
with col1:
    st.markdown(f"<h2 style='margin:0; padding:20px 0;'> A.R.I.A. Command Center</h2>", unsafe_allow_html=True)
with col2:
    if st.button("🚪 Logout", use_container_width=True):
        supabase.auth.sign_out()
        st.session_state.clear()
        st.rerun()

st.markdown("---")

# Tab-based navigation
tabs = st.tabs([
    "📊 Dashboard",
    "🏢 Business Profile",
    " Lead Finder",
    "️ Response Writer",
    " Content Studio",
    "⭐ Review Responses",
    "📱 WhatsApp Studio",
    "🤝 Negotiator"
])

# TAB 1: DASHBOARD
with tabs[0]:
    st.header("Dashboard")
    st.markdown("Welcome back! Here's what's happening with your business today.")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown('<div class="metric-card"><div class="metric-label">Total Leads</div><div class="metric-value">247</div><div class="metric-trend">↑ 12% this week</div></div>', unsafe_allow_html=True)
    with col2:
        st.markdown('<div class="metric-card"><div class="metric-label">AI Generations</div><div class="metric-value">1,429</div><div class="metric-trend">↑ 24% this week</div></div>', unsafe_allow_html=True)
    with col3:
        st.markdown('<div class="metric-card"><div class="metric-label">Emails Sent</div><div class="metric-value">89</div><div class="metric-trend">↑ 8% this week</div></div>', unsafe_allow_html=True)
    with col4:
        st.markdown('<div class="metric-card"><div class="metric-label">Cost Savings</div><div class="metric-value">₹18,400</div><div class="metric-trend">↑ 15% this month</div></div>', unsafe_allow_html=True)
    
    st.markdown('<div class="dashboard-card" style="margin-top:24px;"><h3>Recent Activity</h3><p style="color:#64748B;">Your AI agents are working autonomously. Check the modules below to see drafts and approvals.</p></div>', unsafe_allow_html=True)

# TAB 2: BUSINESS PROFILE
with tabs[1]:
    st.header("Business Profile")
    st.markdown("Configure your business details to personalize all AI outputs.")
    
    with st.form("business_form"):
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
            st.success("✅ Settings saved successfully!")
            st.rerun()

# TAB 3: LEAD FINDER
with tabs[2]:
    st.header("Lead Finder")
    st.markdown("Find real businesses with verified emails in your target market.")
    
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

# TAB 4: RESPONSE WRITER
with tabs[3]:
    st.header("Response Writer")
    st.markdown("Generate professional property profiles and reply emails.")
    
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

# TAB 5: CONTENT STUDIO
with tabs[4]:
    st.header("Content Studio")
    st.markdown("Turn one piece of content into a full week of marketing materials.")
    
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

# TAB 6: REVIEW RESPONSES
with tabs[5]:
    st.header("Review Responses")
    st.markdown("Instantly generate empathetic, brand-safe responses to reviews.")
    
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

# TAB 7: WHATSAPP STUDIO
with tabs[6]:
    st.header("WhatsApp Studio")
    st.markdown("Create engaging WhatsApp broadcasts for your customer list.")
    
    if not user_settings.get('business_name'):
        st.warning("️ Complete Business Profile first!")
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

# TAB 8: NEGOTIATOR
with tabs[7]:
    st.header("Negotiator")
    st.markdown("Lower your business costs with data-driven negotiation emails.")
    
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