from crewai import Agent, Task, Crew, Process, LLM
from crewai_tools import TavilySearchTool

llm = LLM(model="gpt-4o")
tavily_tool = TavilySearchTool()

# --- AGENTS ---
researcher = Agent(
    role="B2B Lead Researcher",
    goal="Find actionable, recent triggers about {company}.",
    backstory="You are an expert B2B researcher. You find specific, recent news, funding, features, or quotes to personalize outreach.",
    llm=llm,
    tools=[tavily_tool],
    verbose=False # Keep console clean, rely on logger
)

writer = Agent(
    role="B2B Copywriter",
    goal="Draft punchy, human-sounding cold emails under 120 words.",
    backstory="You hate AI fluff. You write like a busy, sharp human who respects the prospect's time.",
    llm=llm,
    verbose=False
)

qa_agent = Agent(
    role="Quality Assurance Director",
    goal="Validate factual accuracy, length, tone, and CTA. Output strict JSON.",
    backstory="You are the final gatekeeper. You ensure no hallucinations, strict word counts (<120 words), and a clear low-friction CTA.",
    llm=llm,
    verbose=False
)

# --- TASKS ---
research_task = Task(
    description="""
    Research {company} ({website}). Find ONE recent trigger (news, funding, feature, or quote from {contact_title}).
    If cached research is provided: {cached_research}, use it. Otherwise, search the web.
    Summarize the trigger clearly.
    """,
    expected_output="A concise summary of the company and one specific recent trigger.",
    agent=researcher
)

write_task = Task(
    description="""
    Draft a cold email to {contact_name} at {company}.
    Pitch: AI automation workflows that save operations teams 20 hours a week.
    Rules: Mention the specific trigger found by the researcher. Under 120 words. Low-friction CTA.
    """,
    expected_output="A raw draft of the cold email.",
    agent=writer
)

qa_task = Task(
    description="""
    Review the draft. Verify:
    1. Factual accuracy (no hallucinated triggers).
    2. Length is strictly under 120 words.
    3. Tone is human, punchy, and professional.
    4. Contains a low-friction CTA.
    
    YOU MUST OUTPUT ONLY VALID JSON WITH THIS EXACT FORMAT:
    {{"subject": "Your subject line here", "body": "Hi [Name],\\n\\n..."}}
    Do not include markdown formatting like ```json. Just the raw JSON string.
    """,
    expected_output="Valid JSON string with 'subject' and 'body' keys.",
    agent=qa_agent
)

# --- CREW ---
aria_crew = Crew(
    agents=[researcher, writer, qa_agent],
    tasks=[research_task, write_task, qa_task],
    process=Process.sequential,
    verbose=False
)