import csv
import json
import time
import re
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
import logging

from utils.logger import setup_logger
from utils.cache import get_cached_research, save_cache
from agents.crew_setup import aria_crew

logger = setup_logger()

def parse_json_output(raw_output):
    """Safely extract JSON from LLM output, handling potential markdown wrappers."""
    try:
        # Remove markdown code blocks if present
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
    logger.info(f"Starting processing for: {company}")
    
    # 1. Check Cache
    cached_research = get_cached_research(company)
    
    # 2. Prepare Inputs
    crew_inputs = {
        "company": company,
        "website": lead['website'],
        "contact_name": lead['contact_name'],
        "contact_title": lead['contact_title'],
        "cached_research": cached_research if cached_research else "None"
    }
    
    # 3. Retry Logic
    max_retries = 3
    for attempt in range(max_retries):
        try:
            result = aria_crew.kickoff(inputs=crew_inputs)
            raw_output = result.raw
            
            # Cache the successful research to save future API calls
            if not cached_research:
                # Extract researcher's output (first task result) to cache
                research_result = result.tasks_output[0].raw
                save_cache(company, research_result)
            
            parsed = parse_json_output(raw_output)
            
            return {
                "company": company,
                "contact_name": lead['contact_name'],
                "contact_title": lead['contact_title'],
                "subject": parsed.get("subject", ""),
                "body": parsed.get("body", ""),
                "status": "success",
                "processed_at": datetime.now().isoformat(),
                "error_message": ""
            }
            
        except Exception as e:
            error_msg = str(e)
            logger.warning(f"Attempt {attempt + 1} failed for {company}: {error_msg}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # Exponential backoff
            else:
                logger.error(f"Final failure for {company}: {error_msg}")
                return {
                    "company": company,
                    "contact_name": lead['contact_name'],
                    "contact_title": lead['contact_title'],
                    "subject": "",
                    "body": "",
                    "status": "failed",
                    "processed_at": datetime.now().isoformat(),
                    "error_message": error_msg
                }

def run_batch_pipeline(input_file="inputs/leads.csv", output_file="outputs/results.csv", max_workers=3):
    logger.info(f"🚀 Starting A.R.I.A. Production Pipeline (Max Workers: {max_workers})")
    
    # Auto-create sample input if missing
    import os
    os.makedirs('inputs', exist_ok=True)
    os.makedirs('outputs', exist_ok=True)
    
    if not os.path.exists(input_file):
        with open(input_file, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["company", "website", "contact_name", "contact_title"])
            writer.writerow(["Notion", "notion.com", "Ivan Zhao", "CEO"])
            writer.writerow(["Stripe", "stripe.com", "Patrick Collison", "CEO"])
            writer.writerow(["Vercel", "vercel.com", "Guillermo Rauch", "CEO"])
        logger.info(f"✅ Created sample '{input_file}'. Add your leads and run again.")
        return

    # Load leads
    with open(input_file, mode='r', encoding='utf-8') as f:
        leads = list(csv.DictReader(f))
    
    results = []
    
    # Parallel Processing with Progress Bar
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(process_single_lead, lead): lead for lead in leads}
        
        for future in tqdm(as_completed(futures), total=len(leads), desc="Processing Leads"):
            result = future.result()
            results.append(result)
            
            if result['status'] == 'success':
                logger.info(f"✅ Success: {result['company']}")
            else:
                logger.error(f"❌ Failed: {result['company']} - {result['error_message']}")

    # Save Results
    with open(output_file, mode='w', newline='', encoding='utf-8') as f:
        fieldnames = ["company", "contact_name", "contact_title", "subject", "body", "status", "processed_at", "error_message"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)
        
    logger.info(f"🎉 Pipeline complete! Results saved to '{output_file}'")