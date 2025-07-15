import json
import logging
from config import *

logger = logging.getLogger(__name__)

# --- GLOBAL DATA VARIABLES ---
lore_data = {}
player_data = {}
missions_data = {}
secret_missions_data = {}
message_recipients = []


def get_lore_data():
    return lore_data


def get_player_data():
    return player_data


def get_missions_data():
    return missions_data


def get_secret_missions_data():
    return secret_missions_data


def get_message_recipients():
    return message_recipients


def load_data():
    global lore_data, player_data, missions_data, message_recipients, secret_missions_data

    # Load lore data
    try:
        with open(LORE_FILE, 'r', encoding='utf-8') as f:
            lore_data = json.load(f)
        logger.info(f"Lore data ({LORE_FILE}) loaded successfully.")
    except FileNotFoundError:
        logger.error(f"File {LORE_FILE} not found. Please create it.")
        lore_data = {"error": "Lore data file not found."}
    except json.JSONDecodeError:
        logger.error(f"Error decoding JSON in {LORE_FILE}.")
        lore_data = {"error": "Error reading lore data file."}

    # Load player data
    try:
        with open(PLAYERS_FILE, 'r', encoding='utf-8') as f:
            players_list = json.load(f)
            player_data = {int(player['telegram_user_id']): player for player in players_list}
        logger.info(f"Player data ({PLAYERS_FILE}) loaded successfully.")
    except FileNotFoundError:
        logger.error(f"File {PLAYERS_FILE} not found. Please create it.")
        player_data = {}
    except json.JSONDecodeError:
        logger.error(f"Error decoding JSON in {PLAYERS_FILE}.")
        player_data = {}

    # Load missions data
    try:
        with open(MISSIONS_FILE, 'r', encoding='utf-8') as f:
            missions_data = json.load(f)
        logger.info(f"Mission data ({MISSIONS_FILE}) loaded successfully.")
    except FileNotFoundError:
        logger.error(f"File {MISSIONS_FILE} not found. Please create it.")
        missions_data = {}
    except json.JSONDecodeError:
        logger.error(f"Error decoding JSON in {MISSIONS_FILE}.")
        missions_data = {}

    # Load secret missions data
    try:
        with open(SECRET_MISSIONS_FILE, 'r', encoding='utf-8') as f:
            secret_missions_data = json.load(f)
        logger.info(f"Secret mission data ({SECRET_MISSIONS_FILE}) loaded successfully.")
    except FileNotFoundError:
        logger.warning(f"File {SECRET_MISSIONS_FILE} not found. No secret missions will be available.")
        secret_missions_data = {}
    except json.JSONDecodeError:
        logger.error(f"Error decoding JSON in {SECRET_MISSIONS_FILE}.")
        secret_missions_data = {}

    # Load recipients data
    try:
        with open(RECIPIENTS_FILE, 'r', encoding='utf-8') as f:
            message_recipients = json.load(f)
        logger.info(f"Recipients list ({RECIPIENTS_FILE}) loaded successfully.")
    except FileNotFoundError:
        logger.warning(f"File {RECIPIENTS_FILE} not found. Recipients list will be empty.")
        message_recipients = []
    except json.JSONDecodeError:
        logger.error(f"Error decoding JSON in {RECIPIENTS_FILE}.")
        message_recipients = []


def save_player_data():
    try:
        players_list = list(player_data.values())
        with open(PLAYERS_FILE, 'w', encoding='utf-8') as f:
            json.dump(players_list, f, ensure_ascii=False, indent=2)
        logger.info(f"Player data saved to {PLAYERS_FILE}.")
        return True
    except Exception as e:
        logger.error(f"Error saving player data: {e}")
        return False


def save_lore_data():
    try:
        with open(LORE_FILE, 'w', encoding='utf-8') as f:
            json.dump(lore_data, f, ensure_ascii=False, indent=2)
        logger.info(f"Lore data saved to {LORE_FILE}.")
        return True
    except Exception as e:
        logger.error(f"Error saving lore data: {e}")
        return False


def save_missions_data():
    try:
        with open(MISSIONS_FILE, 'w', encoding='utf-8') as f:
            json.dump(missions_data, f, ensure_ascii=False, indent=2)
        logger.info(f"Mission data saved to {MISSIONS_FILE}.")
        return True
    except Exception as e:
        logger.error(f"Error saving mission data: {e}")
        return False


def save_recipients_data():
    try:
        with open(RECIPIENTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(message_recipients, f, ensure_ascii=False, indent=2)
        logger.info(f"Recipients list saved to {RECIPIENTS_FILE}.")
        return True
    except Exception as e:
        logger.error(f"Error saving recipients list: {e}")
        return False