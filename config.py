import os
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
LOG_DIR = BASE_DIR / "logs"

DATA_DIR.mkdir(exist_ok=True)
LOG_DIR.mkdir(exist_ok=True)

load_dotenv(BASE_DIR / ".env")

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "").strip()
BOT_PREFIX = os.getenv("BOT_PREFIX", "!").strip() or "!"
DATABASE_PATH = DATA_DIR / "famibot.db"
GEMINI_API_KEY = ""
GROQ_API_KEY = 'your_groq_key_here'
OPENROUTER_API_KEY = 'your_openrouter_key_here'


test_guild_value = os.getenv("TEST_GUILD_ID", "").strip()
TEST_GUILD_ID = int(test_guild_value) if test_guild_value.isdigit() else None

if not DISCORD_TOKEN:
    raise RuntimeError(
        "Không tìm thấy DISCORD_TOKEN. "
        "Hãy mở file .env và thêm DISCORD_TOKEN=token_cua_ban"
    )