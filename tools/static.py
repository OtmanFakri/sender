from telegram import Bot
from dotenv import load_dotenv
load_dotenv()
import os 
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MODEL = os.getenv("MODEL")

bot = Bot(token=BOT_TOKEN)
