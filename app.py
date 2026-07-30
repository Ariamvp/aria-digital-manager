import os
import json
import re
import uuid
from datetime import datetime, timezone
import streamlit as st
from dotenv import load_dotenv
from crewai import Agent, Task, Crew, Process, LLM
from crewai_tools import TavilySearchTool, ScrapeWebsiteTool
from db import supabase, supabase_admin, get_user_settings, save_user_settings, log_usage, get_usage_stats

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
    /* === GLOBAL === */
    .stApp { 
        background-color: #F8FAFC; 
        font-family: 'Inter', -apple-system, sans-serif; 
    }
    
    /* Hide Streamlit defaults */
    #MainMenu {visibility: hidden;} 
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* === TABS === */
    .stTabs [data-baseweb="tab-list"] { 
        gap: 8px; 
        background-color: transparent;
        padding: 0;
        border-bottom: 2px solid #E2E8F0;
    }
    .stTabs [data-baseweb="tab"] { 
        background-color: white;
        border-radius: 8px 8px 0 0;
        padding: 12px 24px;
        font-weight: 600;
        color: #64748B;
        border: 2px solid #E2E8F0;
        border-bottom: none;
        transition: all 0.2s;
    }
    .stTabs [data-baseweb="tab"]:hover {
        border-color: #16A34A;
        color: #16A34A;
    }
    .stTabs [aria-selected="true"] { 
        background-color: #16A34A;
        color: white;
        border-color: #16A34A;
        border-bottom: 2px solid #16A34A;
    }
    
    /* === CARDS & CONTAINERS === */
    .dashboard-card, .stForm {
        background: white;
        border: 2px solid #E2E8F0;
        border-radius: 12px;
        padding: 28px;
        margin-bottom: 24px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.04);
    }
    
    /* === INPUT FIELDS - HIGH VISIBILITY === */
    .stTextInput > div > div > input, 
    .stTextArea > div > div > textarea, 
    .stSelectbox > div > div > div,
    .stNumberInput > div > div > input {
        background-color: #FFFFFF !important;
        color: #0F172A !important;
        border: 2px solid #CBD5E1 !important;
        border-radius: 8px !important;
        padding: 12px 16px !important;
        font-size: 14px !important;
        font-weight: 500 !important;
        transition: all 0.2s !important;
    }
    
    /* Input focus state - Green highlight */
    .stTextInput > div > div > input:focus, 
    .stTextArea > div > div > textarea:focus, 
    .stSelectbox > div > div > div:focus,
    .stNumberInput > div > div > input:focus {
        border-color: #16A34A !important;
        border-width: 3px !important;
        box-shadow: 0 0 0 4px rgba(22, 163, 74, 0.1) !important;
        outline: none !important;
    }
    
    /* Input hover state */
    .stTextInput > div > div > input:hover, 
    .stTextArea > div > div > textarea:hover {
        border-color: #16A34A !important;
    }
    
    /* Labels */
    .stTextInput label, .stTextArea label, .stSelectbox label, .stRadio label {
        color: #374151 !important;
        font-weight: 700 !important;
        font-size: 14px !important;
        margin-bottom: 8px !important;
        display: block !important;
    }
    
    /* === BUTTONS === */
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #16A34A 0%, #15803D 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: 700 !important;
        font-size: 15px !important;
        padding: 14px 28px !important;
        box-shadow: 0 4px 6px rgba(22, 163, 74, 0.2) !important;
        transition: all 0.2s !important;
    }
    .stButton > button[kind="primary"]:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 12px rgba(22, 163, 74, 0.3) !important;
    }
    
    .stButton > button[kind="secondary"] {
        background-color: white !important;
        color: #16A34A !important;
        border: 2px solid #16A34A !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        padding: 12px 24px !important;
        transition: all 0.2s !important;
    }
    .stButton > button[kind="secondary"]:hover {
        background-color: #F0FDF4 !important;
        border-color: #15803D !important;
    }
    
    /* === METRICS === */
    .metric-card {
        background: white;
        border: 2px solid #E2E8F0;
        border-radius: 12px;
        padding: 24px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.04);
        transition: all 0.2s;
    }
    .metric-card:hover {
        border-color: #16A34A;
        box-shadow: 0 4px 8px rgba(0,0,0,0.08);
        transform: translateY(-2px);
    }
    .metric-label { font-size: 13px; color: #64748B; margin-bottom: 8px; font-weight: 600; }
    .metric-value { font-size: 32px; font-weight: 800; color: #0F172A; }
    .metric-trend { font-size: 12px; color: #16A34A; margin-top: 4px; font-weight: 600; }
    
    /* === SECTION HEADERS === */
    h1, h2, h3 {
        color: #0F172A !important;
        font-weight: 700 !important;
    }
    
    /* === RADIO BUTTONS === */
    .stRadio > div {
        background: white;
        border: 2px solid #E2E8F0;
        border-radius: 8px;
        padding: 12px;
    }
    
    /* === CHAT MESSAGES === */
    .chat-message {
        padding: 16px;
        border-radius: 12px;
        margin-bottom: 16px;
        border: 2px solid #E2E8F0;
    }
    .user-message {
        background: #F0FDF4;
        border-color: #16A34A;
    }
    .ai-message {
        background: #F8FAFC;
        border-color: #CBD5E1;
    }
    
    /* === QUICK ACTION BUTTONS === */
    div[data-testid="stHorizontalBlock"] button[kind="secondary"] {
        border: 2px solid #E2E8F0 !important;
        background: white !important;
        color: #374151 !important;
        font-weight: 600 !important;
        padding: 14px !important;
        border-radius: 8px !important;
        transition: all 0.2s !important;
    }
    div[data-testid="stHorizontalBlock"] button[kind="secondary"]:hover {
        border-color: #16A34A !important;
        background: #F0FDF4 !important;
        color: #16A34A !important;
        transform: translateY(-2px);
    }
    
    /* === FORM CONTAINERS === */
    div[data-testid="stForm"] {
        border: 2px solid #E2E8F0 !important;
        border-radius: 12px !important;
        padding: 24px !important;
        background: white !important;
    }
    
    /* === SLIDER === */
    .stSlider > div {
        background: white;
        border: 2px solid #E2E8F0;
        border-radius: 8px;
        padding: 12px;
    }
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
# 4. CREW DEFINITIONS (INDUSTRY-AGNOSTIC)
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
    analyst = Agent(role="Content Strategist", goal="Analyze source material and adapt for any industry", backstory="Master strategist who creates platform-specific content for hospitality, retail, services, FMCG, and more", llm=llm, verbose=False)
    blog_writer = Agent(role="SEO Content Writer", goal="Write engaging, industry-appropriate content", backstory="Versatile writer who adapts tone for different business types", llm=llm, verbose=False)
    social_manager = Agent(role="Social Media Expert", goal="Create viral, platform-optimized posts", backstory="Social media specialist for diverse industries", llm=llm, verbose=False)
    newsletter_writer = Agent(role="Email Marketing Specialist", goal="Write high-converting newsletters", backstory="Email expert who knows what drives engagement", llm=llm, verbose=False)
    qa = Agent(role="Content QA", goal="Ensure content is professional and on-brand", backstory="Quality checker for all content types", llm=llm, verbose=False)
    
    return Crew(agents=[analyst, blog_writer, social_manager, newsletter_writer, qa], tasks=[
        Task(description="""
        Analyze this source content:
        "{source_content}"
        
        Target Audience: {target_audience}
        Industry Context: {industry}
        
        Create platform-specific content that:
        1. Adapts tone to the industry (hospitality=warm, retail=professional, etc.)
        2. Uses appropriate keywords for SEO
        3. Includes relevant emojis for social media
        4. Maintains brand consistency
        
        Output as JSON with these keys:
        - blog: 500-word SEO article
        - linkedin: Professional post (150 words)
        - twitter: Thread (3-5 tweets)
        - instagram: Caption with hashtags (100 words)
        - newsletter: Email (200 words)
        """, expected_output="JSON with blog, linkedin, twitter, instagram, newsletter", agent=analyst)
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
    writer = Agent(role="Business Communication Specialist", goal="Create professional business profiles and inquiry responses for ANY industry", backstory="Expert at adapting communication style to different business types - hospitality, retail, services, FMCG, etc.", llm=llm, verbose=False)
    return Crew(agents=[writer], tasks=[
        Task(description="""
        You received this inquiry: 
        "{incoming_request}"
        
        Business details: 
        "{raw_business_details}"
        
        Business Name: {business_name}
        Industry: {industry}
        
        Generate TWO things:
        
        === PART 1: BUSINESS PROFILE/PROPOSAL ===
        Create a professional profile or proposal that includes:
        - Overview of the business
        - Products/Services offered
        - Key features/benefits
        - Pricing/packages (if applicable)
        - Contact information
        - Call to action
        
        IMPORTANT: Adapt the format based on the business type:
        - For Hotels/Resorts: Include rooms, amenities, rates, location
        - For Restaurants: Include menu highlights, cuisine type, ambiance
        - For Retail: Include product categories, brands, special offers
        - For Services: Include service packages, expertise, portfolio
        - For FMCG: Include product range, distribution, pricing
        
        === PART 2: PROFESSIONAL EMAIL RESPONSE ===
        Write a concise email (<150 words):
        1. Extract sender name from inquiry. If blank, use "Valued Customer".
        2. Start "Dear [Name],"
        3. Thank them for their inquiry about {business_name}
        4. Reference their specific question/need
        5. Say "Please find our detailed information above."
        6. Include a clear call-to-action
        7. Sign off professionally using: {contact_info}
        
        OUTPUT FORMAT:
        Profile/Proposal first, then "---EMAIL---" marker, then email.
        """, expected_output="Profile/Proposal + ---EMAIL--- + Email", agent=writer)
    ], process=Process.sequential, verbose=False)

@st.cache_resource
def create_review_crew():
    llm = LLM(model="gpt-4o")
    responder = Agent(role="Customer Experience Specialist", goal="Write empathetic, industry-appropriate review responses", backstory="Expert in reputation management for hospitality, retail, restaurants, and service businesses", llm=llm, verbose=False)
    return Crew(agents=[responder], tasks=[
        Task(description="""
        Respond to this {sentiment} review:
        
        Reviewer: {reviewer_name}
        Review: "{review_text}"
        
        BUSINESS CONTEXT:
        - Business Name: {business_name}
        - Industry: {industry}
        - Contact: {contact_info}
        
        RULES:
        - If POSITIVE: Thank them warmly, mention specific details they praised, reference what makes your business special (based on industry), invite them back.
        - If NEGATIVE: Apologize sincerely and specifically, validate their concern without being defensive, explain what you're doing to fix it, offer offline resolution.
        - If MIXED: Thank them for positive feedback, address concerns professionally, show commitment to improvement.
        
        INDUSTRY-SPECIFIC TONE:
        - Hospitality: Warm, welcoming, personal
        - Restaurant: Enthusiastic about food, apologetic about service
        - Retail: Professional, solution-oriented
        - Services: Expert, reassuring
        - FMCG: Quality-focused, customer-centric
        
        Keep under 150 words. Sign as: {contact_info}
        """, expected_output="Professional review response", agent=responder)
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
# 5. AI CHAT ASSISTANT
# ==========================================
def get_ai_response(user_message, user_settings):
    msg_lower = user_message.lower()
    business_name = user_settings.get('business_name', 'your business')
    
    if any(word in msg_lower for word in ['hello', 'hi', 'help', 'start', 'begin', 'welcome']):
        return f"""
👋 **Welcome to A.R.I.A.!**

I'm your AI assistant, here to help you get the most out of the platform.

**I can help you with:**
- 🎯 Finding new business leads
- ✉️ Writing professional responses to leads
- ⭐ Managing customer reviews
- 🎨 Creating marketing content
- 📱 Sending WhatsApp broadcasts
- 💰 Negotiating with vendors

**Quick Start:**
1. First, complete your **Business Profile** (tab above)
2. Then try any of the AI tools
3. Or ask me anything about how to use them!

**What would you like to do first?**
"""
    elif any(word in msg_lower for word in ['lead', 'find', 'customer', 'client', 'prospect']):
        return "🎯 **Lead Finder** - Your Business Development Tool\n\n**What it does:** Scans the internet for businesses in your target area, verifies emails, and finds contact details.\n\n**How to use:** Click the **Lead Finder** tab, enter your target category and location, and click 'Find Leads'."
    elif any(word in msg_lower for word in ['review', 'response', 'reply', 'feedback', 'rating']):
        return "⭐ **Review Responses** - Protect Your Reputation\n\n**What it does:** Reads customer reviews and drafts professional, empathetic responses tailored to your industry.\n\n**How to use:** Click the **Review Responses** tab, paste the review, select sentiment, and generate."
    elif any(word in msg_lower for word in ['whatsapp', 'broadcast', 'message', 'campaign']):
        return "📱 **WhatsApp Studio** - Engage Your Customers\n\n**What it does:** Creates engaging WhatsApp broadcast messages with emojis, formatting, and clear CTAs.\n\n**How to use:** Click the **WhatsApp Studio** tab, select broadcast type, enter details, and generate."
    elif any(word in msg_lower for word in ['content', 'social media', 'post', 'marketing', 'blog']):
        return "🎨 **Content Studio** - Repurpose Your Content\n\n**What it does:** Takes one piece of content and creates a full week of marketing materials (blogs, social posts, newsletters) adapted to your industry.\n\n**How to use:** Click the **Content Studio** tab, paste your source material, and generate."
    elif any(word in msg_lower for word in ['vendor', 'negotiate', 'cost', 'price', 'discount']):
        return "💰 **Negotiator** - Reduce Your Business Costs\n\n**What it does:** Researches competitor pricing and drafts professional negotiation emails to help you save money.\n\n**How to use:** Click the **Negotiator** tab, enter vendor details and current cost, and generate."
    elif any(word in msg_lower for word in ['response', 'reply', 'lead', 'inquiry', 'customer']):
        return "✉️ **Response Writer** - Convert Leads to Customers\n\n**What it does:** Creates professional business profiles/proposals and drafts personalized email responses tailored to your industry.\n\n**How to use:** Click the **Response Writer** tab, paste the inquiry, and generate."
    elif any(word in msg_lower for word in ['profile', 'settings', 'business', 'configure', 'setup']):
        return "🏢 **Business Profile** - Your Foundation\n\nAll AI tools use your business profile to personalize outputs. Click the **Business Profile** tab, fill in your details (especially Industry), and save."
    elif any(word in msg_lower for word in ['trial', 'pricing', 'cost', 'upgrade', 'payment']):
        return "💳 **Pricing & Trial Information**\n\n- ✅ 14-Day Free Trial Active\n- **Professional Plan:** ₹2,999/month (500 AI generations)\n- **Enterprise Plan:** ₹4,999/month (Unlimited)\n\nNo credit card required for trial!"
    else:
        return f"""
🤖 **I'm here to help!**

I can guide you through using any of A.R.I.A.'s features.

**Try asking me:**
- "How do I find new leads?"
- "How do I respond to reviews?"
- "How do I create content?"
- "How do I send WhatsApp messages?"

Or just tell me what you want to accomplish, and I'll guide you!
"""

# ==========================================
# 6. MAIN APP LOGIC
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

if 'chat_messages' not in st.session_state:
    st.session_state['chat_messages'] = [
        {"role": "assistant", "content": f"""👋 **Welcome to A.R.I.A., {user_email.split('@')[0]}!**\n\nI'm your AI assistant. I can help you:\n- 🎯 Find new business leads\n- ✉️ Write professional responses\n- ⭐ Manage customer reviews\n- 🎨 Create marketing content\n- 📱 Send WhatsApp broadcasts\n- 💰 Negotiate with vendors\n\n**What would you like to do first?**"""}
    ]

col1, col2 = st.columns([6, 1])
with col1:
    st.markdown(f"<h2 style='margin:0; padding:20px 0;'>🔥 A.R.I.A. Command Center</h2>", unsafe_allow_html=True)
with col2:
    if st.button("🚪 Logout", use_container_width=True):
        supabase.auth.sign_out()
        st.session_state.clear()
        st.rerun()

st.markdown("---")

tabs = st.tabs([
    "📊 Dashboard",
    "🏢 Business Profile",
    "💬 AI Chat",
    "🎯 Lead Finder",
    "✉️ Response Writer",
    "🎨 Content Studio",
    "⭐ Review Responses",
    "📱 WhatsApp Studio",
    "🤝 Negotiator"
])

# TAB 1: DASHBOARD
with tabs[0]:
    st.header("Dashboard")
    st.markdown("Welcome back! Here's what's happening with your business today.")
    
    stats = get_usage_stats(st.session_state['user'].id)
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f'<div class="metric-card"><div class="metric-label">Total Leads</div><div class="metric-value">{stats["total_leads"]}</div><div class="metric-trend">↑ Tracked automatically</div></div>', unsafe_allow_html=True)
    with col2:
        st.markdown(f'<div class="metric-card"><div class="metric-label">AI Generations</div><div class="metric-value">{stats["total_generations"]}</div><div class="metric-trend">↑ All modules combined</div></div>', unsafe_allow_html=True)
    with col3:
        st.markdown(f'<div class="metric-card"><div class="metric-label">Emails Sent</div><div class="metric-value">{stats["emails_sent"]}</div><div class="metric-trend">↑ Tracked automatically</div></div>', unsafe_allow_html=True)
    with col4:
        st.markdown('<div class="metric-card"><div class="metric-label">Cost Savings</div><div class="metric-value">₹0</div><div class="metric-trend">Start using AI to save!</div></div>', unsafe_allow_html=True)
    
    st.markdown('<div class="dashboard-card" style="margin-top:24px;"><h3>Recent Activity</h3><p style="color:#64748B;">Your AI agents are working autonomously. Check the modules below to see drafts and approvals.</p></div>', unsafe_allow_html=True)

# TAB 2: BUSINESS PROFILE
with tabs[1]:
    st.header("Business Profile")
    st.markdown("Configure your business details to personalize all AI outputs.")
    
    with st.form("business_form", clear_on_submit=False):
        col1, col2 = st.columns(2)
        with col1:
            biz_name = st.text_input("Business Name *", value=user_settings.get('business_name', ''))
            industry = st.selectbox("Industry", ["Hospitality", "Food/FMCG", "Service", "Retail", "Other"], 
                                   index=0 if not user_settings.get('industry') else 
                                   ["Hospitality", "Food/FMCG", "Service", "Retail", "Other"].index(user_settings.get('industry', 'Hospitality')))
            location = st.text_input("Primary Location *", value=user_settings.get('location', ''))
        with col2:
            contact_info = st.text_input("Contact Info (Name | Phone | Email) *", value=user_settings.get('contact_info', ''))
            biz_pitch = st.text_area("Core Pitch *", height=100, value=user_settings.get('business_pitch', ''))
        
        st.markdown("---")
        st.subheader("🔐 Integration Credentials")
        st.markdown("*These will be encrypted before saving to the database*")
        
        col3, col4 = st.columns(2)
        with col3:
            gmail_pw = st.text_input("Gmail App Password", type="password", value=user_settings.get('gmail_app_password', ''), help="Enter your Gmail App Password")
            tg_token = st.text_input("Telegram Bot Token", type="password", value=user_settings.get('telegram_bot_token', ''), help="Get this from @BotFather on Telegram")
        with col4:
            tg_chat = st.text_input("Telegram Chat ID", value=user_settings.get('telegram_chat_id', ''), help="Your Telegram chat ID for notifications")
        
        submitted = st.form_submit_button("💾 Save Settings", type="primary", use_container_width=True)
        
        if submitted:
            st.info("⏳ Saving... Please wait.")
            settings_data = {
                "business_name": biz_name, "industry": industry, "location": location,
                "contact_info": contact_info, "business_pitch": biz_pitch,
                "gmail_app_password": gmail_pw, "telegram_bot_token": tg_token, "telegram_chat_id": tg_chat
            }
            try:
                result = save_user_settings(st.session_state['user'].id, settings_data)
                if result:
                    st.success("✅ Settings saved successfully and encrypted!")
                    st.balloons()
                    st.rerun()
                else:
                    st.error("❌ Save failed - no data returned from database")
            except Exception as e:
                st.error(f"❌ Error saving settings: {str(e)}")

# TAB 3: AI CHAT
with tabs[2]:
    st.header("💬 AI Chat Assistant")
    st.markdown("Ask me anything about using A.R.I.A. I'm here to help!")
    
    for message in st.session_state['chat_messages']:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    st.markdown("### 💡 Quick Questions")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🎯 How do I find leads?", use_container_width=True):
            st.session_state['chat_messages'].append({"role": "user", "content": "How do I find leads?"})
            st.session_state['chat_messages'].append({"role": "assistant", "content": get_ai_response("How do I find leads?", user_settings)})
            st.rerun()
        if st.button("⭐ How do I manage reviews?", use_container_width=True):
            st.session_state['chat_messages'].append({"role": "user", "content": "How do I manage reviews?"})
            st.session_state['chat_messages'].append({"role": "assistant", "content": get_ai_response("How do I manage reviews?", user_settings)})
            st.rerun()
    with col2:
        if st.button("📱 How do I send WhatsApp?", use_container_width=True):
            st.session_state['chat_messages'].append({"role": "user", "content": "How do I send WhatsApp?"})
            st.session_state['chat_messages'].append({"role": "assistant", "content": get_ai_response("How do I send WhatsApp?", user_settings)})
            st.rerun()
        if st.button("🎨 How do I create content?", use_container_width=True):
            st.session_state['chat_messages'].append({"role": "user", "content": "How do I create content?"})
            st.session_state['chat_messages'].append({"role": "assistant", "content": get_ai_response("How do I create content?", user_settings)})
            st.rerun()
    
    st.markdown("---")
    if prompt := st.chat_input("Type your question here..."):
        st.session_state['chat_messages'].append({"role": "user", "content": prompt})
        st.session_state['chat_messages'].append({"role": "assistant", "content": get_ai_response(prompt, user_settings)})
        st.rerun()
    
    if len(st.session_state['chat_messages']) > 1:
        if st.button("🗑️ Clear Chat", type="secondary"):
            st.session_state['chat_messages'] = [{"role": "assistant", "content": f"👋 **Welcome to A.R.I.A., {user_email.split('@')[0]}!**\n\nI'm your AI assistant. I can help you:\n- 🎯 Find new business leads\n- ✉️ Write professional responses\n- ⭐ Manage customer reviews\n- 🎨 Create marketing content\n- 📱 Send WhatsApp broadcasts\n- 💰 Negotiate with vendors\n\n**What would you like to do first?**"}]
            st.rerun()

# TAB 4: LEAD FINDER
with tabs[3]:
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
                log_usage(st.session_state['user'].id, 'leadgen')
                with st.spinner("Searching..."):
                    crew = create_prospect_finder_crew()
                    result = crew.kickoff(inputs={"category": category, "location": location_search, "num_leads": num_leads})
                    st.success("✅ Leads Found!")
                    st.code(result.raw, language="json")

# TAB 5: RESPONSE WRITER
with tabs[4]:
    st.header("Response Writer")
    st.markdown("Generate professional business profiles/proposals and reply emails.")
    with st.form("response_form"):
        incoming = st.text_area("Incoming Lead Request", height=100)
        raw_details = st.text_area("Your Business Details", height=150, value=user_settings.get('business_pitch', ''))
        if st.form_submit_button("✨ Generate Response", type="primary"):
            log_usage(st.session_state['user'].id, 'response')
            with st.spinner("Crafting..."):
                crew = create_response_crew()
                result = crew.kickoff(inputs={
                    "incoming_request": incoming, 
                    "raw_business_details": raw_details, 
                    "business_name": user_settings.get('business_name', 'Your Business'), 
                    "industry": user_settings.get('industry', 'General'),
                    "contact_info": user_settings.get('contact_info', '')
                })
                st.success("✅ Generated!")
                parts = result.raw.split("---EMAIL---")
                st.markdown(parts[0])
                if len(parts) > 1:
                    st.divider()
                    st.markdown(parts[1])

# TAB 6: CONTENT STUDIO
with tabs[5]:
    st.header("Content Studio")
    st.markdown("Turn one piece of content into a full week of marketing materials.")
    with st.form("content_form"):
        st.markdown("### 📝 Source Material")
        source = st.text_area("Paste your content here", height=150, placeholder="Paste your blog post, video transcript, social media caption, or describe your image/video here...")
        uploaded_file = st.file_uploader("OR upload an image/video", type=['jpg', 'jpeg', 'png', 'mp4', 'mov'], help="Upload a photo or video, then describe what it shows in the text box above")
        
        if uploaded_file is not None:
            st.success(f"✅ Uploaded: {uploaded_file.name}")
            st.info("💡 **Tip:** Now describe what's in this image/video in the text box above, and A.R.I.A. will create content around it!")
        
        audience = st.text_input("Target Audience", placeholder="e.g., Couples and families looking for peaceful getaway")
        
        if st.form_submit_button("🔄 Repurpose Content", type="primary"):
            if not source and uploaded_file is None:
                st.error("⚠️ Please either paste text content OR upload a file with a description!")
            elif not source and uploaded_file is not None:
                st.error("⚠️ You uploaded a file but didn't describe it. Please add a description in the text box above.")
            else:
                log_usage(st.session_state['user'].id, 'content')
                with st.spinner("Analyzing..."):
                    full_source = f"[Image/Video: {uploaded_file.name}] {source}" if uploaded_file is not None else source
                    crew = create_repurposing_crew()
                    result = crew.kickoff(inputs={"source_content": full_source, "target_audience": audience, "industry": user_settings.get('industry', 'General')})
                    parsed = parse_json_output(result.raw)
                    st.success("✅ Content Generated!")
                    
                    st.subheader("📝 Blog Post")
                    st.markdown(parsed.get('blog', 'Not generated'))
                    st.subheader("💼 LinkedIn Post")
                    st.markdown(parsed.get('linkedin', 'Not generated'))
                    st.subheader("🐦 Twitter Thread")
                    st.markdown(parsed.get('twitter', 'Not generated'))
                    st.subheader("📸 Instagram Caption")
                    st.markdown(parsed.get('instagram', 'Not generated'))
                    st.subheader("📧 Newsletter Email")
                    st.markdown(parsed.get('newsletter', 'Not generated'))

# TAB 7: REVIEW RESPONSES
with tabs[6]:
    st.header("Review Responses")
    st.markdown("Instantly generate empathetic, brand-safe responses to reviews.")
    with st.form("review_form"):
        col1, col2 = st.columns(2)
        with col1: reviewer = st.text_input("Reviewer Name")
        with col2: sentiment = st.radio("Sentiment", ["Positive", "Negative", "Mixed"], horizontal=True)
        review_text = st.text_area("Review Text", height=120)
        if st.form_submit_button("✨ Generate Response", type="primary"):
            log_usage(st.session_state['user'].id, 'review')
            with st.spinner("Writing..."):
                crew = create_review_crew()
                result = crew.kickoff(inputs={
                    "reviewer_name": reviewer, 
                    "review_text": review_text, 
                    "sentiment": sentiment, 
                    "business_name": user_settings.get('business_name', 'Your Business'),
                    "industry": user_settings.get('industry', 'General'),
                    "contact_info": user_settings.get('contact_info', '')
                })
                st.success("✅ Response Generated!")
                st.markdown(result.raw)

# TAB 8: WHATSAPP STUDIO
with tabs[7]:
    st.header("WhatsApp Studio")
    st.markdown("Create engaging WhatsApp broadcasts for your customer list.")
    if not user_settings.get('business_name'):
        st.warning("⚠️ Complete Business Profile first!")
    else:
        with st.form("whatsapp_form"):
            col1, col2 = st.columns(2)
            with col1: btype = st.selectbox("Broadcast Type", ["Special Offer", "Festival Greeting", "Welcome Back"])
            with col2: audience = st.selectbox("Target Audience", ["All Customers", "VIP Customers", "New Customers"])
            details = st.text_area("Offer Details", height=120)
            if st.form_submit_button("✨ Generate Broadcast", type="primary"):
                log_usage(st.session_state['user'].id, 'whatsapp')
                with st.spinner("Creating..."):
                    crew = create_whatsapp_crew()
                    result = crew.kickoff(inputs={"business_name": user_settings['business_name'], "broadcast_type": btype, "specific_details": details, "contact_info": user_settings.get('contact_info', '')})
                    st.success("✅ Broadcast Generated!")
                    st.code(result.raw, language="text")

# TAB 9: NEGOTIATOR
with tabs[8]:
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
                log_usage(st.session_state['user'].id, 'vendor')
                with st.spinner("Researching..."):
                    crew = create_negotiation_crew()
                    result = crew.kickoff(inputs={"vendor_name": v_name, "current_service": v_service, "monthly_cost": v_cost, "contract_end_date": v_date, "contact_info": user_settings['contact_info']})
                    parsed = parse_json_output(result.raw)
                    st.success("✅ Draft Generated!")
                    st.code(parsed.get('body', ''), language="text")