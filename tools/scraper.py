from crewai.tools import BaseTool
import json
import requests
from tools.utilis import extract_clean_posts
from .static import bot, CHAT_ID
from telegram import InlineKeyboardMarkup, InlineKeyboardButton, Update
from .database import save_job, update_job_status, delete_job

def scrape_linkedin_feed(cookies_file='cookies.json'):
    try:
        with open(cookies_file, 'r') as f:
            cookies_list = json.load(f)
    except FileNotFoundError:
        print(f"Error: {cookies_file} not found.")
        return
    except Exception as e:
        print(f"Error loading cookies: {e}")
        return

    # Create session and set cookies
    session = requests.Session()
    for cookie in cookies_list:
        session.cookies.set(
            cookie['name'],
            cookie['value'],
            domain=cookie.get('domain', '.linkedin.com')  # Default to .linkedin.com
        )

    # Set headers (User-Agent to mimic browser; update as needed)
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
        "Csrf-Token": session.cookies.get("JSESSIONID", "").strip('"'),
        "Accept": "application/vnd.linkedin.normalized+json+2.1",
        "X-RestLi-Protocol-Version": "2.0.0"
    })

    # Voyager API endpoint for feed (adjust count for more posts)
    url = 'https://www.linkedin.com/voyager/api/feed/updates'
    params = {
        'q': 'chronFeed',  
        'start': 0,
        'count':50  
    }

    # Make request
    try:
        response = session.get(url, params=params)
        response.raise_for_status()  
        data = response.json()

        clened = extract_clean_posts(data["included"])

        return clened
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
    except ValueError:
        print("Invalid JSON response; endpoint or auth may have changed.")

class LinkedInScrapeTool(BaseTool):
    name: str = "LinkedIn Feed Scraper"
    description: str = "Scrapes LinkedIn posts and returns list of post objects"

    def _run(self) -> str:
        posts = scrape_linkedin_feed()
        return str(posts)

async def handle_button(update: Update, context):
    query = update.callback_query
    await query.answer()

    if query.data.startswith("yes_"):
        job_id = int(query.data.split("_")[1])
        update_job_status(job_id, "yes")
        await query.edit_message_text(text=f"✅ YES - Job ID {job_id} status updated to 'yes'")
    elif query.data.startswith("no_"):
        job_id = int(query.data.split("_")[1])
        delete_job(job_id)
        await query.edit_message_text(text=f"❌ NO - Job ID {job_id} deleted from database")



class MessageSenderTool(BaseTool):
    name: str = "Message Sender"
    description: str = "Sends messages via bot to user with job ID for Yes/No confirmation"

    async def _run(self, message: str, job_id: int) -> str:
        # Run async function in sync context
        full_message = f"Job ID: {job_id}\n\n{message}"

        keyboard = [
            [
                InlineKeyboardButton("✅ Yes", callback_data=f"yes_{job_id}"),
                InlineKeyboardButton("❌ No", callback_data=f"no_{job_id}"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await bot.send_message(chat_id=CHAT_ID, text=full_message, reply_markup=reply_markup)
        return f"Message sent with job ID {job_id}: {message}"


class DatabaseSaveTool(BaseTool):
    name: str = "Database Save Tool"
    description: str = "Saves job (link and text) to database and returns the job ID"

    def _run(self, link: str, text: str) -> str:
        job_id = save_job(link, text)
        return f"Job saved with ID: {job_id}"


class SimpleMessageTool(BaseTool):
    name: str = "Simple Message Tool"
    description: str = "Sends simple text messages to Telegram without buttons"

    async def _run(self, message: str) -> str:
        await bot.send_message(chat_id=CHAT_ID, text=message)
        return f"Simple message sent: {message}"