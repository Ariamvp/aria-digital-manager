import os
import csv
import json
import time
import re
import logging
import smtplib
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
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
        logging.FileHandler('logs/aria_local_pipeline.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("ARIA_Local_Pipeline")

# SAFETY TOGGLE: Set to True ONLY when ready to send
AUTO_SEND_ENABLED = True 

# ==========================================
# 2. CACHING LOGIC
# ==========================================
CACHE_FILE = "research_cache_local.json"

def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_cache(company, research_data):
    cache = load_cache()
    cache[company] = research_data
    with open(CACHE_FILE, 'w', encoding='utf-8') as f:
        json.dump(cache, f, indent=2)

# ==========================================
# 3. GMAIL DELIVERY FUNCTION
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
        return "Sent"
    except Exception as e:
        logger.error(f"Gmail SMTP Error: {e}")
        return f"Failed: {str(e)}"

# ==========================================
# 4. CREWAI AGENTS & TASKS FACTORY (LOCAL BUSINESS FOCUS)
# ==========================================
def create_crew():
    llm = LLM(model="gpt-4o")
    tavily_tool = TavilySearchTool()

    researcher = Agent(
        role="Local Business Development Researcher",
        goal="Find recent triggers about {company} related to tourism, retail expansion, corporate events, or growth in Kerala/India.",
        backstory="You are an expert in the Kerala hospitality and FMCG market. You find specific, recent news, new branches, event hosting, or growth milestones to personalize outreach.",
        llm=llm,
        tools=[tavily_tool],
        verbose=False
    )

    writer = Agent(
        role="Partnership & Sales Copywriter",
        goal="Draft warm, professional, relationship-building B2B outreach emails under 120 words.",
        backstory="You specialize in local business partnerships. You write with warmth, professionalism, and a focus on trust, hygiene, authenticity, and mutual growth. Zero AI fluff.",
        llm=llm,
        verbose=False
    )

    qa_agent = Agent(
        role="Quality Assurance Director",
        goal="Validate factual accuracy, local relevance, tone, and CTA. Output strict JSON.",
        backstory="You ensure the email sounds like a genuine local business owner reaching out, not a robot. You enforce strict word counts (<120 words) and clear, low-friction CTAs.",
        llm=llm,
        verbose=False
    )

    research_task = Task(
        description="""
        Research {company} ({website}). Find ONE recent trigger (new branch, tourism spike, corporate event hosting, retail expansion, or growth milestone).
        If cached research is provided: {cached_research}, use it instead of searching.
        Summarize the trigger clearly.
        """,
        expected_output="A concise summary of the company and one specific recent trigger.",
        agent=researcher
    )

    write_task = Task(
        description="""
        Draft a personalized B2B partnership email to {contact_name} at {company}.
        
        OUR BUSINESS CONTEXT TO PITCH: {business_focus}
        
        Rules: 
        1. Mention the specific recent trigger found by the researcher naturally.
        2. Connect their trigger to OUR BUSINESS CONTEXT smoothly.
        3. Tone: Warm, professional, trustworthy, and concise (strictly under 120 words).
        4. End with a low-friction CTA tailored to the business type (e.g., "Can I send our pickle catalog?", "Would you like to see our group booking rates?", or "Can we schedule a quick tasting/call?").
        """,
        expected_output="A raw draft of the partnership email.",
        agent=writer
    )

    qa_task = Task(
        description="""
        Review the draft. Verify:
        1. Factual accuracy (no hallucinated triggers).
        2. Length is strictly under 120 words.
        3. Tone is warm, professional, and locally relevant (not generic tech-bro).
        4. Contains a clear, low-friction CTA.
        
        YOU MUST OUTPUT ONLY VALID JSON WITH THIS EXACT FORMAT:
        {{"subject": "Your subject line here", "body": "Hi [Name],\\n\\n..."}}
        Do not include markdown formatting like ```json. Just the raw JSON string.
        """,
        expected_output="Valid JSON string with 'subject' and 'body' keys.",
        agent=qa_agent
    )

    return Crew(
        agents=[researcher, writer, qa_agent],
        tasks=[research_task, write_task, qa_task],
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

def process_single_lead(lead):
    company = lead['company']
    prospect_email = lead.get('prospect_email', '')
    logger.info(f"Starting processing for: {company}")
    
    cached_research = load_cache().get(company)
    
    crew_inputs = {
        "company": company,
        "website": lead['website'],
        "contact_name": lead['contact_name'],
        "contact_title": lead['contact_title'],
        "business_focus": lead.get('business_focus', 'Local business partnership'),
        "cached_research": cached_research if cached_research else "None"
    }
    
    crew = create_crew()
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            result = crew.kickoff(inputs=crew_inputs)
            raw_output = result.raw
            
            if not cached_research:
                research_result = result.tasks_output[0].raw
                save_cache(company, research_result)
            
            parsed = parse_json_output(raw_output)
            
            gmail_status = "Skipped (AUTO_SEND=False)"
            if AUTO_SEND_ENABLED and prospect_email:
                logger.info(f"Attempting to send email to {prospect_email}...")
                gmail_status = send_email_via_gmail(prospect_email, parsed.get("subject", ""), parsed.get("body", ""))
            elif AUTO_SEND_ENABLED and not prospect_email:
                gmail_status = "Skipped (No Email Provided)"

            return {
                "company": company,
                "contact_name": lead['contact_name'],
                "contact_title": lead['contact_title'],
                "prospect_email": prospect_email,
                "business_focus": lead.get('business_focus', ''),
                "subject": parsed.get("subject", ""),
                "body": parsed.get("body", ""),
                "status": "success",
                "gmail_status": gmail_status,
                "processed_at": datetime.now().isoformat(),
                "error_message": ""
            }
            
        except Exception as e:
            error_msg = str(e)
            logger.warning(f"Attempt {attempt + 1} failed for {company}: {error_msg}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
            else:
                logger.error(f"Final failure for {company}: {error_msg}")
                return {
                    "company": company,
                    "contact_name": lead['contact_name'],
                    "contact_title": lead['contact_title'],
                    "prospect_email": prospect_email,
                    "business_focus": lead.get('business_focus', ''),
                    "subject": "",
                    "body": "",
                    "status": "failed",
                    "gmail_status": "Failed",
                    "processed_at": datetime.now().isoformat(),
                    "error_message": error_msg
                }

# ==========================================
# 6. BATCH PIPELINE EXECUTION
# ==========================================
def run_batch_pipeline(input_file="leads_local.csv", output_file="results_local.csv", max_workers=3):
    logger.info(f"🚀 Starting A.R.I.A. Local Business Pipeline (Max Workers: {max_workers})")
    if AUTO_SEND_ENABLED:
        logger.warning("⚠️ AUTO_SEND_ENABLED is TRUE. Emails will be sent.")
    else:
        logger.info("🛡️ SAFE MODE: AUTO_SEND_ENABLED is False. Emails will be generated but NOT sent.")
    
    if not os.path.exists(input_file):
        with open(input_file, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["company", "website", "contact_name", "contact_title", "prospect_email", "business_focus"])
            writer.writerow(["Kerala Travel Co.", "keralatravel.com", "Rahul", "Operations Manager", "sts261261@gmail.com", "MYBAE Stay Inn: 8-room boutique stay in Alappuzha (Kalavoor) near Kreupasanam Marine Shrine. 2 family rooms (3 pax) and 6 deluxe rooms (2 pax). Ideal for small corporate offsites or family retreats."])
            writer.writerow(["Spice & Gourmet Distributors", "spicegourmet.in", "Priya", "Procurement Head", "sts261261@gmail.com", "Authentic Homemade Kerala Pickles (Prawn, Fish, Mango, Lemon, Ginger) in premium glass jars (150g to 1kg). Hygienic, traditional recipes, perfect for retail shelves or corporate gifting."])
            writer.writerow(["Cherthala Tech Park HR", "cherthalatech.com", "Amit", "HR Manager", "sts261261@gmail.com", "ONAM VEG Restaurant (Cherthala): Authentic, 100% hygienic vegetarian bulk catering, office lunch boxes, and event dining for corporate teams."])
        logger.info(f"✅ Created sample '{input_file}'. Add your real local leads and run again.")
        return

    with open(input_file, mode='r', encoding='utf-8') as f:
        leads = list(csv.DictReader(f))
    
    results = []
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(process_single_lead, lead): lead for lead in leads}
        
        for future in tqdm(as_completed(futures), total=len(leads), desc="Processing Local Leads"):
            result = future.result()
            results.append(result)
            
            if result['status'] == 'success':
                logger.info(f"✅ Success: {result['company']} (Gmail: {result['gmail_status']})")
            else:
                logger.error(f"❌ Failed: {result['company']} - {result['error_message']}")

    with open(output_file, mode='w', newline='', encoding='utf-8') as f:
        fieldnames = ["company", "contact_name", "contact_title", "prospect_email", "business_focus", "subject", "body", "status", "gmail_status", "processed_at", "error_message"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)
        
    logger.info(f"🎉 Pipeline complete! Results saved to '{output_file}'")

if __name__ == "__main__":
    run_batch_pipeline(
        input_file="leads_local.csv",
        output_file="results_local.csv",
        max_workers=3
    )