from tools.static import BOT_TOKEN, GEMINI_API_KEY, MODEL
from tools.knowledge import content
from crewai.llm import LLM
from crewai import Agent, Task, Crew
from tools.scraper import LinkedInScrapeTool, MessageSenderTool, DatabaseSaveTool, SimpleMessageTool, handle_button
from tools.database import init_database
import asyncio
import os
from telegram.ext import ApplicationBuilder, CallbackQueryHandler

os.environ["CREWAI_STORAGE_DIR"] = "./db"


# Set dummy OpenAI key (in case it's needed anywhere)
# os.environ["CHROMA_OPENAI_API_KEY"] = "dummy"
os.environ["CREWAI_STORAGE_DIR"] = "./db"


# GEMINI
llm = LLM(
    api_key=GEMINI_API_KEY,
    model=MODEL,
)


# Agent 1: LinkedIn Scraper - only scrapes posts
scraper_agent = Agent(
    role="LinkedIn Content Scraper",
    goal="Scrape and extract job posts from LinkedIn feed",
    backstory="""You are a data extraction specialist who scrapes LinkedIn posts
    and extracts job-related content.""",
    tools=[LinkedInScrapeTool()],
    verbose=True,
    llm=llm
)

# Task 1: Scrape LinkedIn posts
scrape_task = Task(
    description=f"""
    **MISSION: Scrape LinkedIn posts and extract job opportunities**

    {content}

    1. Use LinkedInScrapeTool to scrape posts from LinkedIn feed

    2. For each post, check if it's a JOB POST by looking for:
       - Keywords: "hiring", "recrute", "recrutement", "job", "poste", "CDI", "CDD",
         "freelance", "opportunity", "opening", "position", "apply", "postuler",
         "candidature", "CV", "resume", "join our team", "we're hiring"
       - Job titles: "developer", "engineer", "développeur", "ingénieur", "backend",
         "full-stack", "software", "DevOps"

    3. SKIP non-job posts:
       - ❌ Articles, industry news, tips, achievements, motivational content, networking posts

    4. Filter for matching jobs:
       ✅ Backend roles (Python, Django, FastAPI, .NET Core, Spring Boot)
       ✅ Full-Stack roles (Python + Angular/Next.js)
       ✅ Software Engineer positions
       ✅ DevOps roles (Docker, Kubernetes)
       ✅ Remote or Morocco/Tanger locations
       ✅ Junior to Mid-level (1-3 years experience)

    5. Return list of matching jobs with link and formatted text for each job
    """,
    expected_output="""List of matching jobs with:
    - Job link (URL)
    - Formatted job text containing position, company, location, requirements""",
    agent=scraper_agent
)

# Agent 2: Message Sender & Database Manager
message_db_agent = Agent(
    role="Job Message and Database Manager",
    goal="Save jobs to database and send Telegram messages with job details",
    backstory="""You are a database and messaging specialist who saves job information
    to the database and sends formatted messages to users via Telegram.""",
    tools=[DatabaseSaveTool(), MessageSenderTool(), SimpleMessageTool()],
    verbose=True,
    llm=llm
)

# Task 2: Save to database and send messages
message_task = Task(
    description="""
    **MISSION: Save jobs to database and send Telegram messages**

    **IF JOBS FOUND:**
    For each job from the previous task:

    1. Use DatabaseSaveTool to save the job (link, text) to database
       - This returns a job_id

    2. Use MessageSenderTool to send the message with the job_id
       - Format: Message should include job details
       - Include the job_id parameter so user can click Yes/No

    3. Format the message as:
       🎯 JOB MATCH FOUND

       Position: [Job Title]
       Company: [Company Name]
       Location: [Location/Remote]

       Key Requirements:
       - [Requirement 1]
       - [Requirement 2]

       Link: [Post URL]

    **IF NO JOBS FOUND:**
    Use SimpleMessageTool to send this message:
    ❌ NO JOB OPPORTUNITIES FOUND

    No matching job opportunities were found in this search.
    """,
    expected_output="""Confirmation that:
    - If jobs found: All jobs were saved to database with job IDs and sent via Telegram with Yes/No buttons
    - If no jobs found: "No jobs found" message was sent via Telegram""",
    agent=message_db_agent,
    context=[scrape_task]
)

# Create and run crew with both agents
crew = Crew(
    agents=[scraper_agent, message_db_agent],
    tasks=[scrape_task, message_task],
    verbose=True,
    llm=llm
)


def run_crew():
    """Run the crew to scrape and process jobs"""
    print("🔄 Running crew...")
    result = crew.kickoff()
    print("✅ Crew finished")
    return result

async def schedule_crew_task():
    """Run crew immediately, then every 30 minutes"""
    # First run immediately
    try:
        await asyncio.to_thread(run_crew)
    except Exception as e:
        print(f"❌ Error running crew: {e}")

    # Then run every 30 minutes
    while True:
        # Wait 30 minutes (1800 seconds)
        print("⏳ Waiting 30 minutes until next run...")
        await asyncio.sleep(1800)

        try:
            await asyncio.to_thread(run_crew)
        except Exception as e:
            print(f"❌ Error running crew: {e}")

# Main function
async def main():
    # Initialize database
    init_database()
    print("✅ Database initialized")

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Initialize the application
    await app.initialize()

    # Add handlers
    app.add_handler(CallbackQueryHandler(handle_button))

    # Start polling
    await app.start()
    await app.updater.start_polling()

    # Start crew scheduler in background
    crew_task = asyncio.create_task(schedule_crew_task())

    # Keep the bot running
    print("Bot is running... Press Ctrl+C to stop")
    try:
        # Run until interrupted
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        print("Stopping bot...")
        crew_task.cancel()
    finally:
        # Cleanup
        await app.updater.stop()
        await app.stop()
        await app.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
