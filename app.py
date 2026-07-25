import os
import json
import re
import logging
import smtplib
import requests
import uuid
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import streamlit as st
from dotenv import load_dotenv
from crewai import Agent, Task, Crew, Process, LLM
from crewai_tools import TavilySearchTool, ScrapeWebsiteTool

# ==========================================
# 1. INITIALIZATION & CONFIGURATION
# ==========================================
load_dotenv()

st.set_page_config(page_title="A.R.I.A. Command Center", page_icon="🤖", layout="wide")

os.makedirs('logs', exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler('logs/aria_dashboard.log', encoding='utf-8')]
)
logger = logging.getLogger("ARIA_Dashboard")

# Business Pitches Dictionary
BUSINESS_PITCHES = {
    "MYBAE Stay Inn": {
        "name": "MYBAE Stay Inn",
        "pitch": "8-room boutique stay in Alappuzha (Kalavoor) near Kreupasanam Marine Shrine. 2 family rooms (3 pax) and 6 deluxe rooms (2 pax).",
        "contact": "Sujesh T S | 9048081475 | sts261261@gmail.com",
        "target_categories": ["tour operators", "travel agencies", "corporate event planners", "wedding planners", "retreat organizers"],
        "locations": ["Kochi", "Alappuzha", "Kottayam", "Kerala"],
        "email": "mybaerooms@gmail.com"
    },
    "Homemade Kerala Pickles": {
        "name": "Homemade Kerala Pickles",
        "pitch": "Authentic Homemade Kerala Pickles (Prawn, Fish, Mango, Lemon, Ginger) in premium glass jars (150g to 1kg). Hygienic, traditional recipes.",
        "contact": "Sujesh T S | 9048081475 | sts261261@gmail.com",
        "target_categories": ["supermarkets", "organic food stores", "gourmet shops", "corporate gifting companies", "specialty food distributors"],
        "locations": ["Alappuzha", "Kochi", "Cherthala", "Kerala"],
        "email": "mybaepickles@gmail.com"
    }
}

# ==========================================
# AUTHENTICATION CHECK
# ==========================================
def check_password():
    """Returns `True` if the user had the correct password."""
    
    def password_entered():
        """Checks whether a password entered by the user is correct."""
        correct_password = os.getenv("APP_PASSWORD", "admin123")
        if st.session_state["password"] == correct_password:
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.text_input(
            "Password:",
            type="password",
            on_change=password_entered,
            key="password"
        )
        return False
    elif not st.session_state["password_correct"]:
        st.text_input(
            "Password:",
            type="password",
            on_change=password_entered,
            key="password"
        )
        st.error("😕 Password incorrect")
        return False
    else:
        return True

if not check_password():
    st.stop()

# ==========================================
# 2. HELPER FUNCTIONS
# ==========================================
def save_and_notify_telegram(to_address, subject, body, task_type="Draft"):
    """Saves draft to JSON and sends a notification to Telegram for approval."""
    task_id = str(uuid.uuid4())[:8]
    
    task = {
        "id": task_id,
        "to": to_address,
        "subject": subject,
        "body": body,
        "status": "pending",
        "type": task_type
    }
    
    tasks = []
    if os.path.exists("pending_approvals.json"):
        with open("pending_approvals.json", 'r') as f:
            tasks = json.load(f)
    tasks.append(task)
    with open("pending_approvals.json", 'w') as f:
        json.dump(tasks, f, indent=2)
        
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    body_preview = body[:250] + "..." if len(body) > 250 else body
    
    message = f"🤖 *A.R.I.A. Approval Required*\n\n*Type:* {task_type}\n*To:* {to_address}\n*Subject:* {subject}\n\n*Preview:*\n_{body_preview}_\n\nReply with: `send {task_id}` to approve and send."
    
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}
    
    try:
        requests.post(url, json=payload)
        return f"Sent to Telegram (ID: {task_id})"
    except Exception as e:
        return f"Telegram Error: {str(e)}"

def parse_json_output(raw_output):
    try:
        cleaned = re.sub(r'^```json\s*|\s*```$', '', raw_output.strip(), flags=re.MULTILINE)
        return json.loads(cleaned)
    except json.JSONDecodeError:
        subject_match = re.search(r'"subject"\s*:\s*"([^"]+)"', raw_output, re.IGNORECASE)
        body_match = re.search(r'"body"\s*:\s*"((?:\\.|[^"\\])*)"', raw_output, re.IGNORECASE)
        if subject_match and body_match:
            return {"subject": subject_match.group(1), "body": body_match.group(1).replace('\\n', '\n')}
        return {"subject": "Error Parsing Subject", "body": raw_output}

# ==========================================
# 3. CREW 1: VENDOR NEGOTIATION
# ==========================================
@st.cache_resource
def create_negotiation_crew():
    llm = LLM(model="gpt-4o")
    tavily_tool = TavilySearchTool()
    researcher = Agent(role="Pricing Analyst", goal="Find competitor pricing for {current_service}.", backstory="Expert procurement analyst.", llm=llm, tools=[tavily_tool], verbose=False)
    strategist = Agent(role="Procurement Strategist", goal="Develop negotiation leverage.", backstory="Veteran procurement expert.", llm=llm, verbose=False)
    drafter = Agent(role="Copywriter", goal="Draft professional negotiation email.", backstory="Specialist in vendor comms.", llm=llm, verbose=False)
    qa = Agent(role="QA Director", goal="Validate and format as JSON.", backstory="Ensures polish and JSON format.", llm=llm, verbose=False)

    return Crew(agents=[researcher, strategist, drafter, qa], 
                tasks=[
                    Task(description="Research {vendor_name} and {current_service}. Find 2-3 competitors with pricing.", expected_output="Competitor summary.", agent=researcher),
                    Task(description="Develop strategy for {vendor_name}. We pay ${monthly_cost}/mo. Contract ends {contract_end_date}.", expected_output="Strategy.", agent=strategist),
                    Task(description="Draft email to {vendor_name}. Sign as: Sujesh T S, MYBAE Group, sts261261@gmail.com, 9048081475", expected_output="Draft.", agent=drafter),
                    Task(description='Output strict JSON: {"subject": "...", "body": "..."}', expected_output="JSON", agent=qa)
                ], process=Process.sequential, verbose=False)

# ==========================================
# 4. CREW 2: CONTENT REPURPOSING
# ==========================================
@st.cache_resource
def create_repurposing_crew():
    llm = LLM(model="gpt-4o")
    analyst = Agent(role="Content Strategist", goal="Analyze source material.", backstory="Master content strategist.", llm=llm, verbose=False)
    blog_writer = Agent(role="SEO Blog Writer", goal="Write SEO blog post.", backstory="Authoritative blog writer.", llm=llm, verbose=False)
    social_manager = Agent(role="Social Media Manager", goal="Create viral social posts.", backstory="Expert in social algorithms.", llm=llm, verbose=False)
    newsletter_writer = Agent(role="Email Marketing Expert", goal="Write compelling newsletter.", backstory="High open-rate email expert.", llm=llm, verbose=False)
    qa = Agent(role="Content QA", goal="Format as JSON.", backstory="JSON formatter.", llm=llm, verbose=False)

    return Crew(agents=[analyst, blog_writer, social_manager, newsletter_writer, qa],
                tasks=[
                    Task(description="Analyze this source: {source_content}. Target: {target_audience}.", expected_output="Analysis.", agent=analyst),
                    Task(description="Write 500-word SEO blog post.", expected_output="Blog.", agent=blog_writer),
                    Task(description="Write LinkedIn post (<150 words), 5-tweet thread, and IG caption.", expected_output="Social.", agent=social_manager),
                    Task(description="Write newsletter email (<200 words).", expected_output="Newsletter.", agent=newsletter_writer),
                    Task(description='Format ALL into JSON: {"blog": "...", "linkedin": "...", "twitter": "...", "instagram": "...", "newsletter": "..."}', expected_output="JSON", agent=qa)
                ], process=Process.sequential, verbose=False)

# ==========================================
# 5. CREW 3: PROSPECT DISCOVERY
# ==========================================
@st.cache_resource
def create_prospect_finder_crew():
    llm = LLM(model="gpt-4o")
    tavily_tool = TavilySearchTool()
    scrape_tool = ScrapeWebsiteTool()

    finder = Agent(
        role="Lead Discovery Specialist",
        goal="Find and extract detailed information about {category} businesses in {location}.",
        backstory="You are an expert at finding high-quality B2B leads. You search the web, extract company names, websites, contact persons, and emails from business directories, LinkedIn, and company websites.",
        llm=llm,
        tools=[tavily_tool, scrape_tool],
        verbose=False
    )

    qualifier = Agent(
        role="Lead Qualification Analyst",
        goal="Qualify and format the discovered leads into a clean JSON list.",
        backstory="You verify that leads are legitimate businesses and format them properly with all required fields.",
        llm=llm,
        verbose=False
    )

    return Crew(agents=[finder, qualifier],
                tasks=[
                    Task(description="Search for {category} in {location}. Find at least {num_leads} businesses. For each, extract: company name, website, contact person name, job title, and email if available. Use search queries like '{category} in {location}', 'best {category} {location}', '{category} {location} contact'.", expected_output="List of discovered leads with company, website, contact_name, contact_title, email.", agent=finder),
                    Task(description="Format all discovered leads into strict JSON array format: [{'company': '...', 'website': '...', 'contact_name': '...', 'contact_title': '...', 'email': '...'}, ...]", expected_output="JSON array of leads", agent=qualifier)
                ],
                process=Process.sequential,
                verbose=False)

# ==========================================
# 6. CREW 4: LOCAL LEAD OUTREACH
# ==========================================
@st.cache_resource
def create_local_lead_crew():
    llm = LLM(model="gpt-4o")
    tavily_tool = TavilySearchTool()

    researcher = Agent(
        role="Local Business Development Researcher",
        goal="Find recent triggers about {company} related to tourism, retail, or corporate growth in Kerala/India.",
        backstory="Expert in Kerala hospitality and FMCG. Finds specific news, new branches, or growth milestones.",
        llm=llm, tools=[tavily_tool], verbose=False
    )
    writer = Agent(
        role="Partnership Copywriter",
        goal="Draft warm, professional B2B outreach emails under 120 words.",
        backstory="Specializes in local partnerships. Writes with warmth, trust, and zero AI fluff.",
        llm=llm, verbose=False
    )
    qa = Agent(
        role="QA Director",
        goal="Validate tone, length, and output strict JSON.",
        backstory="Ensures emails sound like a genuine local business owner.",
        llm=llm, verbose=False
    )

    return Crew(agents=[researcher, writer, qa],
                tasks=[
                    Task(description="Research {company} ({website}). Find ONE recent trigger (new branch, tourism spike, event hosting).", expected_output="Trigger summary.", agent=researcher),
                    Task(description="Draft partnership email to {contact_name} at {company}. PITCH CONTEXT: {business_focus}. Sign as: Sujesh T S, MYBAE Group, {business_email}, 9048081475. Rules: <120 words, warm tone, mention trigger, low-friction CTA.", expected_output="Draft.", agent=writer),
                    Task(description='Output strict JSON: {"subject": "...", "body": "..."}', expected_output="JSON", agent=qa)
                ], process=Process.sequential, verbose=False)

# ==========================================
# 6.5. CREW 5: LEAD RESPONSE & ASSET COMPILER
# ==========================================
@st.cache_resource
def create_response_crew():
    llm = LLM(model="gpt-4o")
    
    writer = Agent(
        role="Hospitality Partnership Specialist",
        goal="Create a Property Profile AND a reply email",
        backstory="Expert at creating professional property profiles and partnership emails",
        llm=llm,
        verbose=False
    )

    return Crew(agents=[writer],
                tasks=[
                    Task(description="""
                    You have received this inquiry: {incoming_request}
                    
                    And these raw business details: {raw_business_details}
                    
                    Your job is to generate TWO things in this EXACT order:
                    
                    ===================================
                    PART 1: PROPERTY PROFILE
                    ===================================
                    Create a professional, formatted property profile with these sections:
                    
                    # 🏨 PROPERTY PROFILE: MYBAE Stay Inn
                    
                    ## 📍 Location
                    [Extract from raw details]
                    
                    ## 🛏️ Rooms
                    - Family Rooms: [number] ([capacity] persons)
                    - Deluxe Rooms: [number] ([capacity] persons)
                    
                    ## 💰 Rates
                    [List all pricing clearly]
                    
                    ## 🍽️ Meals
                    [What's available]
                    
                    ## ✨ Amenities
                    [List all amenities]
                    
                    ## 📸 Photos
                    [Photo links]
                    
                    ## 🌟 Offers
                    [Special offers]
                    
                    ## 🗺️ Nearby
                    [Attractions]
                    
                    ===================================
                    PART 2: EMAIL REPLY
                    ===================================
                    Write a SHORT email (under 100 words) that:
                    1. Extract the sender's NAME from the inquiry signature
                    2. Start with "Dear [Name],"
                    3. Thank them for interest
                    4. Say "Please find our Property Profile above with all requested details"
                    5. Express enthusiasm
                    6. End with:
                    Warm regards,
                    Sujesh T S
                    MYBAE Group
                    sts261261@gmail.com | 9048081475
                    
                    ===================================
                    OUTPUT FORMAT:
                    ===================================
                    First output the Property Profile (Part 1),
                    Then add a line that says "---EMAIL---"
                    Then output the Email Reply (Part 2)
                    """, 
                    expected_output="Property Profile followed by ---EMAIL--- marker followed by Email Reply", 
                    agent=writer)
                ], 
                process=Process.sequential, 
                verbose=False)

# ==========================================
# 6.6. CREW 6: REVIEW RESPONSE GENERATOR
# ==========================================
@st.cache_resource
def create_review_crew():
    llm = LLM(model="gpt-4o")
    
    responder = Agent(
        role="Hospitality Reputation Manager",
        goal="Write perfect, empathetic, and brand-aligned responses to guest reviews",
        backstory="You are an expert in guest relations and online reputation management for boutique hotels. You know how to turn negative experiences into opportunities and amplify positive ones.",
        llm=llm,
        verbose=False
    )

    return Crew(agents=[responder],
                tasks=[
                    Task(description="""
                    Write a professional response to this {sentiment} review for MYBAE Stay Inn.
                    
                    Reviewer Name: {reviewer_name}
                    Review Text: "{review_text}"
                    
                    STRICT RULES:
                    1. If POSITIVE: Thank them warmly, mention a specific detail they liked, invite them back.
                    2. If NEGATIVE: Apologize sincerely, validate their concern without being defensive, mention we are taking action, offer to take it offline (email: sts261261@gmail.com).
                    3. If MIXED: Thank them for the positive parts, address the negative parts constructively.
                    4. Keep it under 150 words.
                    5. NEVER use generic AI phrases like "We are thrilled" or "We apologize for any inconvenience". Sound like a real human owner.
                    6. Sign off EXACTLY as:
                    Warm regards,
                    Sujesh T S
                    MYBAE Group
                    sts261261@gmail.com | 9048081475
                    """, 
                    expected_output="Professional, human-sounding review response", 
                    agent=responder)
                ], 
                process=Process.sequential, 
                verbose=False)

# ==========================================
# 6.7. CREW 7: WHATSAPP BROADCAST GENERATOR
# ==========================================
@st.cache_resource
def create_whatsapp_crew():
    llm = LLM(model="gpt-4o")
    
    whatsapp_expert = Agent(
        role="WhatsApp Marketing Specialist",
        goal="Create highly engaging, properly formatted WhatsApp broadcast messages that drive action without looking like spam",
        backstory="You are a master of WhatsApp marketing in India. You know exactly how to use bolding, italics, emojis, and spacing to make messages readable, exciting, and highly convertible. You avoid generic AI fluff and write like a trusted local business owner.",
        llm=llm,
        verbose=False
    )

    return Crew(agents=[whatsapp_expert],
                tasks=[
                    Task(description="""
                    Create a WhatsApp broadcast message for the following scenario:
                    
                    Business: {business_name}
                    Context/Pitch: {business_pitch}
                    Contact Info: {contact_info}
                    Broadcast Type: {broadcast_type}
                    Specific Details/Offer: {specific_details}
                    
                    STRICT WHATSAPP FORMATTING RULES:
                    1. Use *asterisks* for bold text (e.g., *Special Offer*)
                    2. Use _underscores_ for italics if needed
                    3. Use relevant, eye-catching emojis (but don't overdo it, max 1-2 per line)
                    4. Keep it concise (under 150 words total). WhatsApp users skim.
                    5. Include a clear, low-friction Call to Action (CTA) with the phone number.
                    6. Add a polite opt-out line at the very bottom (e.g., "Reply STOP to unsubscribe").
                    7. DO NOT use generic AI phrases like "Unlock the power of" or "Elevate your experience". Sound natural, warm, and local.
                    
                    OUTPUT: Just the raw WhatsApp message text, ready to copy-paste. No introductory chatter.
                    """, 
                    expected_output="Perfectly formatted WhatsApp broadcast message", 
                    agent=whatsapp_expert)
                ], 
                process=Process.sequential, 
                verbose=False)

# ==========================================
# 7. STREAMLIT UI
# ==========================================
st.title("🤖 A.R.I.A. Command Center")
st.markdown("Your Autonomous Revenue & Intelligence Agent. Choose your module below.")

with st.sidebar:
    st.header("⚙️ Global Settings")
    st.info("Settings apply to all modules")
    auto_email_global = st.checkbox("Send drafts to Telegram for approval", value=True, help="Sends drafts to your Telegram bot. You must reply 'send [ID]' to actually send the email.")
    st.divider()
    st.markdown("### 📊 Quick Stats")
    st.markdown("- Pipelines: 6 Active")
    st.markdown("- Agents: 15 Ready")
    st.markdown("- Status: 🟢 Online")

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "🤝 Vendor Negotiation", 
    "🔄 Content Repurposing", 
    "🎯 Local Lead Gen", 
    "📩 Lead Response & Assets", 
    "⭐ Review Responses",
    "📱 WhatsApp Broadcasts"
])

# --- TAB 1: VENDOR NEGOTIATION ---
with tab1:
    st.header("Generate data-driven negotiation emails to lower costs.")
    with st.form("negotiation_form"):
        col1, col2 = st.columns(2)
        with col1:
            v_name = st.text_input("Vendor Name *", placeholder="e.g., AWS, Zoom")
            v_service = st.text_input("Current Service *", placeholder="e.g., Cloud Hosting")
            v_cost = st.text_input("Monthly Cost ($) *", placeholder="450")
        with col2:
            v_date = st.text_input("Contract End Date", placeholder="2026-12-31")
            u_email = st.text_input("Your Email (to receive draft) *", value=os.getenv("GMAIL_ADDRESS", ""))
        
        if st.form_submit_button("🚀 Generate Negotiation Draft", type="primary", use_container_width=True):
            if not all([v_name, v_service, v_cost, u_email]):
                st.error("Please fill in all required fields.")
            else:
                with st.spinner("🔍 Researching competitors and drafting..."):
                    try:
                        crew = create_negotiation_crew()
                        result = crew.kickoff(inputs={"vendor_name": v_name, "current_service": v_service, "monthly_cost": v_cost, "contract_end_date": v_date})
                        parsed = parse_json_output(result.raw)
                        st.success("✅ Draft Generated!")
                        st.markdown(f"**Subject:** {parsed.get('subject', 'N/A')}")
                        st.code(parsed.get('body', 'N/A'), language="text")
                        if auto_email_global:
                            status = save_and_notify_telegram(u_email, parsed.get('subject', ''), parsed.get('body', ''), "Vendor Negotiation")
                            st.success(f"📱 {status}!")
                    except Exception as e:
                        st.error(f"Error: {e}")

# --- TAB 2: CONTENT REPURPOSING ---
with tab2:
    st.header("Turn 1 piece of content into a full week of marketing.")
    with st.form("repurpose_form"):
        source_content = st.text_area("Paste Source Material *", height=200, placeholder="Paste article text, YouTube transcript, or rough notes...")
        col1, col2 = st.columns(2)
        with col1:
            target_audience = st.text_input("Target Audience *", placeholder="e.g., SaaS Founders, Local Homeowners")
        with col2:
            brand_tone = st.selectbox("Brand Tone", ["Professional & Authoritative", "Casual & Conversational", "Bold & Disruptive", "Warm & Educational"])
        
        if st.form_submit_button("🔄 Repurpose Content", type="primary", use_container_width=True):
            if not source_content or not target_audience:
                st.error("Please provide source material and target audience.")
            else:
                with st.spinner("🧠 Analyzing content and generating assets..."):
                    try:
                        crew = create_repurposing_crew()
                        result = crew.kickoff(inputs={"source_content": source_content, "target_audience": target_audience})
                        parsed = parse_json_output(result.raw)
                        if "error" in parsed and "subject" not in parsed:
                            st.error("Failed to parse output.")
                        else:
                            st.success("✅ Content Repurposed Successfully!")
                            st.subheader("📝 SEO Blog Post")
                            st.markdown(parsed.get('blog', 'N/A'))
                            col_a, col_b = st.columns(2)
                            with col_a:
                                st.subheader("💼 LinkedIn Post")
                                st.markdown(parsed.get('linkedin', 'N/A'))
                                st.subheader("📧 Newsletter Email")
                                st.markdown(parsed.get('newsletter', 'N/A'))
                            with col_b:
                                st.subheader("🐦 Twitter/X Thread")
                                st.markdown(parsed.get('twitter', 'N/A'))
                                st.subheader("📸 Instagram Caption")
                                st.markdown(parsed.get('instagram', 'N/A'))
                    except Exception as e:
                        st.error(f"Error: {e}")

# --- TAB 3: LOCAL LEAD GEN ---
with tab3:
    st.header("🎯 Automated Lead Discovery & Outreach for Your Businesses")
    subtab_discover, subtab_manual = st.tabs(["🔍 Auto-Discover Prospects", "✏️ Manual Entry"])
    
    with subtab_discover:
        st.info("💡 A.R.I.A. will automatically find prospects and generate personalized outreach!")
        
        st.subheader("1. Select Your Business")
        pitch_type_discover = st.radio("Business Type:", ["Predefined Business", "Custom Business"], horizontal=True, key="pitch_type_discover")
        
        predefined_container = st.container()
        custom_container = st.container()
        
        biz_pitch = ""
        biz_email = ""
        default_cat = ""
        default_loc = ""
        
        if pitch_type_discover == "Predefined Business":
            with predefined_container:
                selected_business = st.selectbox("Which business are you pitching?", list(BUSINESS_PITCHES.keys()), key="discover_business_select")
                biz_pitch = BUSINESS_PITCHES[selected_business]["pitch"]
                biz_email = BUSINESS_PITCHES[selected_business]["email"]
                default_cat = BUSINESS_PITCHES[selected_business]["target_categories"][0]
                default_loc = BUSINESS_PITCHES[selected_business]["locations"][0]
            custom_container.empty()
        else:
            predefined_container.empty()
            with custom_container:
                biz_pitch = st.text_area("Custom Business Pitch Description *", height=100, placeholder="e.g., MYBAE Event Catering: Premium vegetarian catering for weddings and corporate events in Alappuzha.")
                biz_email = st.text_input("Custom Business Email *", placeholder="e.g., catering@mybae.com")
                default_cat = ""
                default_loc = ""
        
        with st.form("discovery_form"):
            st.subheader("2. Discovery Settings")
            col1, col2 = st.columns(2)
            with col1:
                search_category = st.text_input("Target Category to Search *", value=default_cat, placeholder="e.g., tour operators, supermarkets, wedding planners")
                num_leads = st.slider("Number of Leads to Find", min_value=3, max_value=20, value=5)
            with col2:
                search_location = st.text_input("Target Location to Search *", value=default_loc, placeholder="e.g., Kochi, Alappuzha, Cherthala")
            
            submit_discovery = st.form_submit_button("🔍 Discover & Generate Outreach", type="primary", use_container_width=True)
        
        if submit_discovery:
            is_valid = True
            if pitch_type_discover == "Custom Business" and not all([biz_pitch, biz_email, search_category, search_location]):
                st.error("Please fill in all Custom Business and Discovery fields.")
                is_valid = False
            elif pitch_type_discover == "Predefined Business" and not all([search_category, search_location]):
                st.error("Please fill in all required fields.")
                is_valid = False
            
            if is_valid:
                with st.spinner("🤖 A.R.I.A. is discovering prospects and generating personalized outreach... (This may take 2-3 minutes)"):
                    try:
                        st.markdown(f"**Searching for {search_category} in {search_location}...**")
                        discovery_crew = create_prospect_finder_crew()
                        discovery_result = discovery_crew.kickoff(inputs={
                            "category": search_category,
                            "location": search_location,
                            "num_leads": num_leads
                        })
                        
                        try:
                            cleaned_raw = re.sub(r'^```json\s*|\s*```$', '', discovery_result.raw.strip(), flags=re.MULTILINE)
                            discovered_leads = json.loads(cleaned_raw)
                            if isinstance(discovered_leads, dict) and 'leads' in discovered_leads:
                                discovered_leads = discovered_leads['leads']
                            if not isinstance(discovered_leads, list):
                                discovered_leads = []
                        except Exception as e:
                            discovered_leads = []
                            st.warning(f"Could not parse leads as JSON: {e}")
                            st.code(discovery_result.raw)
                        
                        if not discovered_leads:
                            st.error("No leads discovered. Try adjusting the category or location.")
                        else:
                            st.success(f"✅ Found {len(discovered_leads)} prospects!")
                            
                            st.subheader("📋 Discovered Prospects")
                            for idx, lead in enumerate(discovered_leads, 1):
                                comp_name = lead.get('company') or 'Unknown Company'
                                comp_web = lead.get('website') or 'N/A'
                                comp_contact = lead.get('contact_name') or 'Team'
                                comp_title = lead.get('contact_title') or 'Manager'
                                comp_email = lead.get('email') or 'No email found'
                                
                                with st.expander(f"{idx}. {comp_name}"):
                                    st.write(f"**Website:** {comp_web}")
                                    st.write(f"**Contact:** {comp_contact} ({comp_title})")
                                    st.write(f"**Email:** {comp_email}")
                            
                            st.subheader("📧 Generating Personalized Outreach...")
                            progress_bar = st.progress(0)
                            
                            for idx, lead in enumerate(discovered_leads):
                                try:
                                    outreach_crew = create_local_lead_crew()
                                    inputs = {
                                        "company": lead.get('company') or 'Unknown Company',
                                        "website": lead.get('website') or '',
                                        "contact_name": lead.get('contact_name') or 'Team',
                                        "contact_title": lead.get('contact_title') or 'Manager',
                                        "business_focus": biz_pitch,
                                        "business_email": biz_email
                                    }
                                    
                                    result = outreach_crew.kickoff(inputs=inputs)
                                    parsed = parse_json_output(result.raw)
                                    
                                    st.markdown(f"**{idx}. {lead.get('company') or 'Unknown Company'}**")
                                    st.markdown(f"*Subject:* {parsed.get('subject', 'N/A')}")
                                    st.code(parsed.get('body', 'N/A'), language="text")
                                    
                                    lead_email = lead.get('email')
                                    if auto_email_global and isinstance(lead_email, str) and '@' in lead_email:
                                        status_msg = save_and_notify_telegram(lead_email, parsed.get('subject', ''), parsed.get('body', ''), "Local Lead Outreach")
                                        st.caption(f"📱 {status_msg}")
                                    else:
                                        st.caption("⚠️ Skipped Telegram notification: No valid prospect email found. Draft is shown above.")
                                    
                                    progress_bar.progress((idx + 1) / len(discovered_leads))
                                    
                                except Exception as e:
                                    st.error(f"Error generating for {lead.get('company')}: {e}")
                                    logger.error(f"Outreach error: {e}")
                            
                            st.success("✅ Outreach generation complete!")
                            
                    except Exception as e:
                        st.error(f"Error in discovery: {e}")
                        logger.error(f"Discovery error: {e}")
    
    with subtab_manual:
        st.header("Generate hyper-personalized outreach for specific prospects.")
        
        st.subheader("1. Your Business Focus")
        manual_pitch_type = st.radio("Pitch Type:", ["Predefined Business", "Custom Business"], horizontal=True, key="pitch_type_manual")
        
        manual_predefined_container = st.container()
        manual_custom_container = st.container()
        
        biz_focus = ""
        biz_email_manual = ""
        
        if manual_pitch_type == "Predefined Business":
            with manual_predefined_container:
                selected_business_manual = st.selectbox("Which business are you pitching?", list(BUSINESS_PITCHES.keys()), key="manual_business_select")
                biz_focus = BUSINESS_PITCHES[selected_business_manual]["pitch"]
                biz_email_manual = BUSINESS_PITCHES[selected_business_manual]["email"]
            manual_custom_container.empty()
        else:
            manual_predefined_container.empty()
            with manual_custom_container:
                custom_biz_name = st.text_area("Custom Business Pitch Description *", height=100, placeholder="e.g., MYBAE Event Catering: Premium vegetarian catering for weddings.")
                custom_biz_email = st.text_input("Custom Business Email *", placeholder="e.g., catering@mybae.com")
                biz_focus = custom_biz_name
                biz_email_manual = custom_biz_email
        
        with st.form("local_lead_form"):
            st.subheader("2. Prospect Details")
            col1, col2 = st.columns(2)
            with col1:
                l_company = st.text_input("Company Name *", placeholder="e.g., Kerala Travel Co.")
                l_website = st.text_input("Website *", placeholder="e.g., keralatravel.com")
                l_contact = st.text_input("Contact Name *", placeholder="e.g., Rahul")
            with col2:
                l_title = st.text_input("Contact Title *", placeholder="e.g., Operations Manager")
                l_email = st.text_input("Prospect Email *", placeholder="e.g., rahul@keralatravel.com")
            
            submit_manual = st.form_submit_button("🎯 Generate Lead Outreach", type="primary", use_container_width=True)
        
        if submit_manual:
            is_valid_manual = True
            if manual_pitch_type == "Custom Business" and not all([biz_focus, biz_email_manual, l_company, l_website, l_contact, l_title, l_email]):
                st.error("Please fill in all Custom Business and Prospect fields.")
                is_valid_manual = False
            elif manual_pitch_type == "Predefined Business" and not all([l_company, l_website, l_contact, l_title, l_email]):
                st.error("Please fill in all required fields.")
                is_valid_manual = False
            
            if is_valid_manual:
                with st.spinner("🔍 Researching local triggers and drafting outreach..."):
                    try:
                        crew = create_local_lead_crew()
                        inputs = {
                            "company": l_company,
                            "website": l_website,
                            "contact_name": l_contact,
                            "contact_title": l_title,
                            "business_focus": biz_focus,
                            "business_email": biz_email_manual
                        }
                        result = crew.kickoff(inputs=inputs)
                        parsed = parse_json_output(result.raw)
                        
                        st.success("✅ Lead Outreach Generated!")
                        st.markdown(f"**Subject:** {parsed.get('subject', 'N/A')}")
                        st.code(parsed.get('body', 'N/A'), language="text")
                        
                        if auto_email_global:
                            status_msg = save_and_notify_telegram(l_email, parsed.get('subject', ''), parsed.get('body', ''), "Manual Lead Outreach")
                            st.success(f"📱 {status_msg}")
                    except Exception as e:
                        st.error(f"Error: {e}")

# --- TAB 4: LEAD RESPONSE & ASSET COMPILER ---
with tab4:
    st.header("📩 Turn Lead Requests into Closed Deals")
    st.markdown("Paste the lead's email and your raw business details. A.R.I.A. will format a professional profile and draft the perfect reply.")
    
    with st.form("response_form"):
        incoming_request = st.text_area("📥 Paste Incoming Lead Request *", height=150, placeholder="e.g., Dear Mr. Rahul, Thank you for reaching out... Could you please share property profile, tariffs, photos...")
        
        st.markdown("---")
        st.markdown("#### 🏢 Your Raw Business Details")
        st.caption("Don't worry about formatting. Just paste your messy notes, links, or bullet points below. A.R.I.A. will clean it up.")
        raw_business_details = st.text_area("Raw Details *", height=200, placeholder="""e.g., 
- Name: MYBAE Stay Inn, Alappuzha (near Kreupasanam Marine Shrine)
- Rooms: 2 Family (3 pax), 6 Deluxe (2 pax)
- Tariffs: Deluxe ₹3500, Family ₹5000. Group discount 15% for 5+ rooms.
- Meals: Breakfast included. Lunch/Dinner available at ₹400/plate.
- Amenities: Free WiFi, Parking, 24/7 Hot Water, Travel Desk.
- Photos: [Insert Google Drive Link Here]
- Special Offer: Free boat ride voucher for bookings over 3 nights.""")
        
        submit_response = st.form_submit_button("✨ Generate Profile & Reply", type="primary", use_container_width=True)
    
    if submit_response:
        if not incoming_request or not raw_business_details:
            st.error("Please fill in both fields.")
        else:
            with st.spinner("🤖 A.R.I.A. is crafting your response..."):
                try:
                    crew = create_response_crew()
                    result = crew.kickoff(inputs={
                        "incoming_request": incoming_request,
                        "raw_business_details": raw_business_details
                    })
                    
                    st.success("✅ Response Generated Successfully!")
                    
                    raw_text = result.raw
                    
                    if "---EMAIL---" in raw_text:
                        parts = raw_text.split("---EMAIL---")
                        profile_section = parts[0].strip()
                        email_section = parts[1].strip()
                    else:
                        profile_section = raw_text
                        email_section = ""
                    
                    st.subheader("📋 Professional Property Profile")
                    st.markdown(profile_section)
                    st.info("💡 **Copy this profile** → Paste into Notion or save as PDF!")
                    
                    if email_section:
                        st.divider()
                        st.subheader("📧 Email Reply")
                        st.markdown(email_section)
                        st.success("✅ Ready to send!")
                    
                except Exception as e:
                    st.error(f"Error: {e}")
                    logger.error(f"Response crew error: {e}")

# --- TAB 5: REVIEW RESPONSE GENERATOR ---
with tab5:
    st.header("⭐ Review Response Generator")
    st.markdown("Instantly generate professional, empathetic responses to Google, TripAdvisor, or Booking.com reviews.")
    
    with st.form("review_form"):
        reviewer_name = st.text_input("Reviewer Name (Optional)", placeholder="e.g., John Doe or 'Valued Guest'")
        review_text = st.text_area("Paste the Review *", height=150, placeholder="e.g., Great location but the AC wasn't working properly...")
        sentiment = st.radio("Review Sentiment", ["Positive", "Negative", "Mixed/Neutral"], horizontal=True)
        
        submit_review = st.form_submit_button("✨ Generate Response", type="primary", use_container_width=True)
    
    if submit_review:
        if not review_text:
            st.error("Please paste the review text.")
        else:
            with st.spinner("🤖 A.R.I.A. is crafting the perfect response..."):
                try:
                    crew = create_review_crew()
                    result = crew.kickoff(inputs={
                        "reviewer_name": reviewer_name if reviewer_name else "Valued Guest",
                        "review_text": review_text,
                        "sentiment": sentiment
                    })
                    
                    st.success("✅ Response Generated!")
                    st.subheader("📝 Your Response")
                    st.markdown(result.raw)
                    st.info("💡 **Copy and paste** this directly into Google/TripAdvisor!")
                    
                except Exception as e:
                    st.error(f"Error: {e}")
                    logger.error(f"Review crew error: {e}")

# --- TAB 6: WHATSAPP BROADCAST GENERATOR ---
with tab6:
    st.header("📱 WhatsApp Broadcast Generator")
    st.markdown("Create high-converting, perfectly formatted WhatsApp messages for your customers. Ready to copy-paste!")
    
    with st.form("whatsapp_form"):
        col1, col2 = st.columns(2)
        with col1:
            business_select = st.selectbox("Select Business", list(BUSINESS_PITCHES.keys()) + ["Custom Business"])
            
            if business_select == "Custom Business":
                biz_name = st.text_input("Business Name *", placeholder="e.g., My Cafe")
                biz_pitch = st.text_area("What do you do? *", height=80, placeholder="e.g., Premium coffee and snacks in Alappuzha")
                contact_info = st.text_input("Contact Info *", placeholder="e.g., Sujesh | 9048081475")
            else:
                biz_name = BUSINESS_PITCHES[business_select]["name"]
                biz_pitch = BUSINESS_PITCHES[business_select]["pitch"]
                contact_info = BUSINESS_PITCHES[business_select]["contact"]
                st.info(f"Using predefined details for *{biz_name}*")
                
        with col2:
            broadcast_type = st.selectbox("Broadcast Type", [
                "🎉 Festival Greeting (Onam, Vishu, Christmas, etc.)",
                "💰 Special Discount / Offer",
                "⏰ Last-Minute Availability / Urgent",
                "🔄 Welcome Back / Re-engagement (Haven't visited in a while)",
                "🎂 Birthday / Anniversary Wish",
                "📢 New Product / Service Launch"
            ])
            
            specific_details = st.text_area("Specific Details / Offer *", height=100, placeholder="e.g., 15% off for 3+ nights, valid till Aug 30. Free breakfast included.")
        
        submit_whatsapp = st.form_submit_button("✨ Generate WhatsApp Message", type="primary", use_container_width=True)
    
    if submit_whatsapp:
        if not specific_details:
            st.error("Please provide specific details or the offer.")
        else:
            with st.spinner("🤖 A.R.I.A. is crafting your WhatsApp broadcast..."):
                try:
                    crew = create_whatsapp_crew()
                    result = crew.kickoff(inputs={
                        "business_name": biz_name,
                        "business_pitch": biz_pitch,
                        "contact_info": contact_info,
                        "broadcast_type": broadcast_type,
                        "specific_details": specific_details
                    })
                    
                    st.success("✅ WhatsApp Message Generated!")
                    st.subheader("📱 Ready to Copy-Paste")
                    
                    # Display in a code block so formatting (asterisks) is preserved exactly for WhatsApp
                    st.code(result.raw, language="text")
                    
                    st.info("💡 **Pro Tip:** Click the 'Copy' button in the top right of the black box above, then paste directly into WhatsApp Web or your phone!")
                    
                except Exception as e:
                    st.error(f"Error: {e}")
                    logger.error(f"WhatsApp crew error: {e}")