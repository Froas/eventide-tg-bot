import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- CONFIGURATION ---
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_TELEGRAM_BOT_TOKEN")
DM_CHAT_ID_STR = os.getenv("DM_CHAT_ID")
DM_CHAT_ID = int(DM_CHAT_ID_STR) if DM_CHAT_ID_STR and DM_CHAT_ID_STR.isdigit() else None

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# File paths from .env or defaults
LORE_FILE = os.path.join(BASE_DIR, os.getenv("LORE_FILE_PATH", "data/lore_data.json"))
PLAYERS_FILE = os.path.join(BASE_DIR, os.getenv("PLAYERS_FILE_PATH", "data/player_data.json"))
MISSIONS_FILE = os.path.join(BASE_DIR, os.getenv("MISSIONS_FILE_PATH", "data/missions_data.json"))
RECIPIENTS_FILE = os.path.join(BASE_DIR, os.getenv("RECIPIENTS_FILE_PATH", "data/recipients_data.json"))
SECRET_MISSIONS_FILE = os.path.join(BASE_DIR, os.getenv("SECRET_MISSIONS_FILE_PATH", "data/secret_missions_data.json"))

# --- PLAYER STATUSES ---
STATUS_ACTIVE_ON_MISSION = "Active (on mission)"
STATUS_ARRESTED = "Arrested"
STATUS_HACKED = "Hacked"
STATUS_TRAITOR = "Traitor"
STATUS_DEAD = "Dead"
STATUS_UNDEFINED = "Undefined"

VALID_PLAYER_STATUSES = [
    STATUS_ACTIVE_ON_MISSION,
    STATUS_ARRESTED,
    STATUS_HACKED,
    STATUS_TRAITOR,
    STATUS_DEAD,
    STATUS_UNDEFINED,
]

# --- CONVERSATION HANDLER STATES ---
CHOOSE_RECIPIENT, TYPE_MESSAGE = range(2)
SELECT_PLAYER_FOR_ACTION = range(10, 11)
CHOOSE_BROADCAST_TARGET, TYPE_BROADCAST_SENDER_NAME, TYPE_BROADCAST_MESSAGE_TEXT, CONFIRM_BROADCAST_SEND = range(20, 24)
SELECT_DM_PLAYER, TYPE_DM_SENDER_NAME, TYPE_DM_MESSAGE_TEXT, CONFIRM_DM_SEND = range(30, 34)
SELECT_PLAYER_FOR_STATUS, SELECT_NEW_STATUS = range(40, 42)
SELECT_PLAYER_FOR_SECRET_MISSION, CHOOSE_SECRET_MISSION = range(50, 52)

# Welcome image file_id cache
WELCOME_IMAGE_FILE_ID = None