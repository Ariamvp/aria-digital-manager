import os
import csv
import json
import time
import re
import logging
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
from crewai import Agent, Task, Crew, Process, LLM
from crewai_tools import TavilySearchTool

# ==========================================
# 1. INITIALIZATION & LOGGING
# ==========================================
load_dotenv()

os.makedirs('logs', exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/vendor_negotiation.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("Vendor_Negotiation")

# SAFETY TOGGLE: Set to True ONLY when ready to send drafts to yourself for review
AUTO_SEND_DRAFTS = True

# ==========================================
# 2. CACHING LOGIC (For common vendors like AWS, Azure, etc.)
# ==========================================
CACHE_FILE = "vendor_research_cache.json"

def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_cache(vendor, research_data):
    cache = load_cache()
    cache[vendor] = research_data
    with open(CACHE_FILE, 'w', encoding='utf-8') as f:
        json.dump(cache, f, indent=2)

# ==========================================
# 3. GMAIL DELIVERY FUNCTION (For sending drafts to you)
# ==========================================
def send_email_via_gmail(to_address, subject, body):
    from_address = os.getenv("GMAIL_ADDRESS")
    app_password = os.getenv("GMAIL_APP_PASSWORD")
    
    if not from_address or not app_password:
        raise ValueError("GMAIL_ADDRESS or GMAIL_APP_PASSWORD missing in .env")

    msg = MIMEMultipart()
    msg['From'] = from_address
    msg['To'] = to_address
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(from_address, app_password)
        server.send_message(msg)
        server.quit()
        return "Draft Sent"
    except Exception as e:
        logger.error(f"Gmail SMTP Error: {e}")
        return f"Failed: {str(e)}"

# ==========================================
# 4. CREWAI AGENTS & TASKS FACTORY
# ==========================================
def create_negotiation_crew():
    llm = LLM(model="gpt-4o")
    tavily_tool = TavilySearchTool()

    # Agent 1: Research competitor pricing and market rates
    pricing_researcher = Agent(
        role="Vendor Pricing Intelligence Analyst",
        goal="Find competitor pricing, alternative vendors, and market rates for {current_service}.",
        backstory="You are an expert procurement analyst. You dig deep to find exact competitor pricing, better alternatives, and industry benchmarks to give the negotiation team maximum leverage.",
        llm=llm,
        tools=[tavily_tool],
        verbose=False
    )

    # Agent 2: Develop the negotiation strategy
    negotiation_strategist = Agent(
        role="Senior Procurement Strategist",
        goal="Analyze the pricing research and develop a negotiation strategy with specific leverage points.",
        backstory="You are a veteran procurement expert with 20 years of experience. You know exactly how to position competitor alternatives to secure better rates without damaging vendor relationships.",
        llm=llm,
        verbose=False
    )

    # Agent 3: Draft the negotiation email
    email_drafter = Agent(
        role="Vendor Relations Copywriter",
        goal="Draft a professional, firm, but relationship-preserving negotiation email.",
        backstory="You specialize in vendor communications. You write emails that are polite but firm, reference specific leverage points, and propose clear next steps. You never sound aggressive or desperate.",
        llm=llm,
        verbose=False
    )

    # Agent 4: QA check the email
    qa_agent = Agent(
        role="Negotiation Quality Assurance Director",
        goal="Validate the email is professional, has clear leverage, and outputs strict JSON.",
        backstory="You ensure every negotiation email is polished, references real competitor data, and has a clear CTA. You catch any aggressive tone or weak leverage points.",
        llm=llm,
        verbose=False
    )

    # Task 1: Research competitor pricing
    research_task = Task(
        description="""
        Research {vendor_name} and their {current_service} offering.
        
        Find:
        1. At least 2-3 direct competitors offering similar services with their pricing.
        2. Industry benchmarks or average market rates for this service.
        3. Any recent news about {vendor_name} (funding, new features, pricing changes).
        
        If cached research is provided: {cached_research}, use it instead of searching.
        
        Output a clear summary with specific competitor names and pricing.
        """,
        expected_output="A detailed summary of competitor pricing, alternatives, and market benchmarks.",
        agent=pricing_researcher
    )

    # Task 2: Develop negotiation strategy
    strategy_task = Task(
        description="""
        Based on the pricing research, develop a negotiation strategy for {vendor_name}.
        
        Current situation:
        - We pay ${monthly_cost}/month for {current_service}
        - Contract ends: {contract_end_date}
        
        Your strategy should include:
        1. The top 2-3 leverage points (specific competitor alternatives with pricing).
        2. The target discount or improvement we should ask for (e.g., "15% discount" or "match competitor X's pricing of $Y").
        3. The negotiation angle (e.g., "long-term partnership", "competitive bid", "budget constraints").
        
        Be specific and data-driven.
        """,
        expected_output="A clear negotiation strategy with specific leverage points and target outcomes.",
        agent=negotiation_strategist
    )

    # Task 3: Draft the negotiation email
    draft_task = Task(
        description="""
        Draft a professional vendor negotiation email to {vendor_name}.
        
        Context:
        - We currently pay ${monthly_cost}/month for {current_service}
        - Contract ends: {contract_end_date}
        
        Use the negotiation strategy and leverage points from the strategist.
        
        Rules:
        1. Tone: Professional, firm, but relationship-preserving. Never aggressive.
        2. Reference the long-term partnership (if applicable).
        3. Mention 1-2 specific competitor alternatives with pricing (this is the key leverage).
        4. Propose a specific target (e.g., "15% discount" or "match competitor X's pricing").
        5. End with a low-friction CTA (e.g., "Can we schedule a 10-min call this week to discuss?").
        6. Keep it under 200 words.
        """,
        expected_output="A professional negotiation email draft.",
        agent=email_drafter
    )

    # Task 4: QA check and format as JSON
    qa_task = Task(
        description="""
        Review the negotiation email draft. Verify:
        1. Professional tone (not aggressive or desperate).
        2. References specific competitor pricing (real leverage).
        3. Proposes a clear target (specific discount or pricing match).
        4. Has a low-friction CTA.
        5. Under 200 words.
        
        YOU MUST OUTPUT ONLY VALID JSON WITH THIS EXACT FORMAT:
        {{"subject": "Negotiation: [Service] - [Your Company]", "body": "Hi [Vendor Contact],\\n\\n..."}}
        Do not include markdown formatting like ```json. Just the raw JSON string.
        """,
        expected_output="Valid JSON string with 'subject' and 'body' keys.",
        agent=qa_agent
    )

    return Crew(
        agents=[pricing_researcher, negotiation_strategist, email_drafter, qa_agent],
        tasks=[research_task, strategy_task, draft_task, qa_task],
        process=Process.sequential,
        verbose=False
    )

# ==========================================
# 5. PROCESSING & PARSING LOGIC
# ==========================================
def parse_json_output(raw_output):
    try:
        cleaned = re.sub(r'^```json\s*|\s*```$', '', raw_output.strip(), flags=re.MULTILINE)
        return json.loads(cleaned)
    except json.JSONDecodeError:
        logger.warning("Failed to parse JSON, attempting fallback regex.")
        subject_match = re.search(r'"subject"\s*:\s*"([^"]+)"', raw_output, re.IGNORECASE)
        body_match = re.search(r'"body"\s*:\s*"((?:\\.|[^"\\])*)"', raw_output, re.IGNORECASE)
        if subject_match and body_match:
            return {"subject": subject_match.group(1), "body": body_match.group(1).replace('\\n', '\n')}
        return {"subject": "Error Parsing Subject", "body": raw_output}

def process_single_vendor(vendor_data):
    vendor_name = vendor_data['vendor_name']
    your_email = vendor_data.get('your_email', '')
    logger.info(f"Starting negotiation research for: {vendor_name}")
    
    cached_research = load_cache().get(vendor_name)
    
    crew_inputs = {
        "vendor_name": vendor_name,
        "current_service": vendor_data['current_service'],
        "monthly_cost": vendor_data['monthly_cost'],
        "contract_end_date": vendor_data.get('contract_end_date', 'N/A'),
        "cached_research": cached_research if cached_research else "None"
    }
    
    crew = create_negotiation_crew()
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            result = crew.kickoff(inputs=crew_inputs)
            raw_output = result.raw
            
            if not cached_research:
                research_result = result.tasks_output[0].raw
                save_cache(vendor_name, research_result)
            
            parsed = parse_json_output(raw_output)
            
            # Send draft to your email for review
            email_status = "Skipped (AUTO_SEND_DRAFTS=False)"
            if AUTO_SEND_DRAFTS and your_email:
                logger.info(f"Sending negotiation draft to {your_email}...")
                email_status = send_email_via_gmail(your_email, parsed.get("subject", ""), parsed.get("body", ""))
            elif AUTO_SEND_DRAFTS and not your_email:
                email_status = "Skipped (No Email Provided)"

            return {
                "vendor_name": vendor_name,
                "current_service": vendor_data['current_service'],
                "monthly_cost": vendor_data['monthly_cost'],
                "contract_end_date": vendor_data.get('contract_end_date', ''),
                "your_email": your_email,
                "subject": parsed.get("subject", ""),
                "body": parsed.get("body", ""),
                "status": "success",
                "email_status": email_status,
                "processed_at": datetime.now().isoformat(),
                "error_message": ""
            }
            
        except Exception as e:
            error_msg = str(e)
            logger.warning(f"Attempt {attempt + 1} failed for {vendor_name}: {error_msg}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
            else:
                logger.error(f"Final failure for {vendor_name}: {error_msg}")
                return {
                    "vendor_name": vendor_name,
                    "current_service": vendor_data['current_service'],
                    "monthly_cost": vendor_data['monthly_cost'],
                    "contract_end_date": vendor_data.get('contract_end_date', ''),
                    "your_email": your_email,
                    "subject": "",
                    "body": "",
                    "status": "failed",
                    "email_status": "Failed",
                    "processed_at": datetime.now().isoformat(),
                    "error_message": error_msg
                }

# ==========================================
# 6. BATCH PIPELINE EXECUTION
# ==========================================
def run_negotiation_pipeline(input_file="vendors_to_negotiate.csv", output_file="negotiation_drafts.csv"):
    logger.info(f"🚀 Starting A.R.I.A. Vendor Negotiation Pipeline")
    if AUTO_SEND_DRAFTS:
        logger.warning("⚠️ AUTO_SEND_DRAFTS is TRUE. Drafts will be emailed to you for review.")
    else:
        logger.info("🛡️ SAFE MODE: AUTO_SEND_DRAFTS is False. Drafts will be saved to CSV only.")
    
    if not os.path.exists(input_file):
        with open(input_file, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["vendor_name", "current_service", "monthly_cost", "contract_end_date", "your_email"])
            writer.writerow(["AWS", "Cloud Hosting (EC2 + S3)", "450", "2026-12-31", "sts261261@gmail.com"])
            writer.writerow(["Adobe Creative Cloud", "Design Software Suite", "80", "2026-09-15", "sts261261@gmail.com"])
            writer.writerow(["Office Internet Provider", "Business Fiber Internet (500Mbps)", "120", "2026-06-30", "sts261261@gmail.com"])
        logger.info(f"✅ Created sample '{input_file}'. Add your real vendors and run again.")
        return

    with open(input_file, mode='r', encoding='utf-8') as f:
        vendors = list(csv.DictReader(f))
    
    results = []
    
    for vendor in vendors:
        result = process_single_vendor(vendor)
        results.append(result)
        
        if result['status'] == 'success':
            logger.info(f"✅ Success: {result['vendor_name']} (Email: {result['email_status']})")
        else:
            logger.error(f"❌ Failed: {result['vendor_name']} - {result['error_message']}")

    with open(output_file, mode='w', newline='', encoding='utf-8') as f:
        fieldnames = ["vendor_name", "current_service", "monthly_cost", "contract_end_date", "your_email", "subject", "body", "status", "email_status", "processed_at", "error_message"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)
        
    logger.info(f"🎉 Pipeline complete! Negotiation drafts saved to '{output_file}'")

if __name__ == "__main__":
    run_negotiation_pipeline(
        input_file="vendors_to_negotiate.csv",
        output_file="negotiation_drafts.csv"
    )