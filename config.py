import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MIRO_ACCESS_TOKEN = os.getenv("MIRO_ACCESS_TOKEN")
MIRO_BOARD_ID = os.getenv("MIRO_BOARD_ID")

# Read the allowed users string and parse it into a list of integers
allowed_users_raw = os.getenv("ALLOWED_USERS", "")
ALLOWED_USERS = [int(uid.strip()) for uid in allowed_users_raw.split(",") if uid.strip().isdigit()]

# Read base URL from .env or fallback to standard OpenAI URL if not specified
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://openai.com")

if not all([TELEGRAM_TOKEN, OPENAI_API_KEY, MIRO_ACCESS_TOKEN, MIRO_BOARD_ID]):
    raise ValueError("CRITICAL: variables are not defined in .env!")


if not ALLOWED_USERS:
    raise ValueError("CRITICAL: security Error: ALLOWED_USERS list is empty! Add at least one Telegram ID to .env.")