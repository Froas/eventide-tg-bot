import logging
import json
import os
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove, \
    Message
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    CallbackQueryHandler,
    ConversationHandler,
)
from telegram.constants import ParseMode

# Load environment variables from .env file
load_dotenv()

# --- CONFIGURATION ---
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_TELEGRAM_BOT_TOKEN")
DM_CHAT_ID_STR = os.getenv("DM_CHAT_ID")
DM_CHAT_ID = int(DM_CHAT_ID_STR) if DM_CHAT_ID_STR and DM_CHAT_ID_STR.isdigit() else None

if not BOT_TOKEN or BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN":
    logging.error("BOT_TOKEN not found or not set in .env file or environment variables. Please set it.")
if DM_CHAT_ID is None:
    logging.error("DM_CHAT_ID not found or not a valid integer in .env file or environment variables. Please set it.")
if not BOT_TOKEN or BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN" or DM_CHAT_ID is None:
    exit("Critical configuration missing. Please set BOT_TOKEN and DM_CHAT_ID in your .env file or environment.")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# File paths from .env or defaults
LORE_FILE = os.path.join(BASE_DIR, os.getenv("LORE_FILE_PATH", "data/lore_data.json"))
PLAYERS_FILE = os.path.join(BASE_DIR, os.getenv("PLAYERS_FILE_PATH", "data/player_data.json"))
MISSIONS_FILE = os.path.join(BASE_DIR, os.getenv("MISSIONS_FILE_PATH", "data/missions_data.json"))
RECIPIENTS_FILE = os.path.join(BASE_DIR, os.getenv("RECIPIENTS_FILE_PATH", "data/recipients_data.json"))
SECRET_MISSIONS_FILE = os.path.join(BASE_DIR, os.getenv("SECRET_MISSIONS_FILE_PATH", "data/secret_missions_data.json"))

# --- LOGGING SETUP ---
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- GLOBAL DATA VARIABLES ---
lore_data = {}
player_data = {}
missions_data = {}
secret_missions_data = {}
message_recipients = []
# NEW: A single, static file_id for the welcome image to avoid complex logic in start_command
# You can get this ID by sending the image to your bot once and then to a bot like @JsonDumpBot
# Or leave as None to upload it once on the first /start command and cache it.
WELCOME_IMAGE_FILE_ID = None

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


# --- DATA MANAGEMENT FUNCTIONS ---
def load_data():
    global lore_data, player_data, missions_data, message_recipients, secret_missions_data
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

    try:
        with open(RECIPIENTS_FILE, 'r', encoding='utf-8') as f:
            message_recipients = json.load(f)
        logger.info(f"Recipients list ({RECIPIENTS_FILE}) loaded successfully.")
    except FileNotFoundError:
        logger.warning(
            f"File {RECIPIENTS_FILE} not found. Recipients list will be empty. Use /admin_recipients add to add recipients.")
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


# NEW: Function to save lore data, necessary for caching image file_ids
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


# --- UTILITY FUNCTIONS ---
def is_admin(user_id: int) -> bool:
    return user_id == DM_CHAT_ID


def get_player_status(user_id: int) -> str:
    player = player_data.get(user_id)
    if player:
        return player.get("status", STATUS_UNDEFINED)
    return STATUS_UNDEFINED


def is_player_active(user_id: int) -> bool:
    player = player_data.get(user_id)
    return player.get("is_active", False) if player else False


# --- KEYBOARD FUNCTIONS ---
def get_main_reply_keyboard(user_id: int) -> ReplyKeyboardMarkup:
    keyboard = [
        ["📚 Lore"],
        ["👤 My character", "🎯 My mission"],
        ["✉️ Send a message"]
    ]
    if is_admin(user_id):
        keyboard.append(["⚙️ Admin Panel"])
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def get_admin_panel_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [
        ["List Players", "Activate Player", "Deactivate Player"],
        ["Set Player Status", "Set Secret Mission"],
        ["Broadcast Message", "Send Direct Message"],
        ["Update Mission", "Update Character", "Manage Recipients"],
        ["⬅️ Back to Main Menu"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)


def get_lore_main_menu_keyboard() -> InlineKeyboardMarkup | None:
    keyboard_buttons = []
    if "error" in lore_data:
        return None
    for key, item in lore_data.items():
        if isinstance(item, dict) and "title" in item:
            cb_key = f"lore_{key}"
            keyboard_buttons.append([InlineKeyboardButton(item["title"], callback_data=cb_key[:60])])
        elif isinstance(item, str) and key == "introduction":
            cb_key = f"lore_{key}"
            keyboard_buttons.append(
                [InlineKeyboardButton("📜 Introduction to Eventide: Eclipse", callback_data=cb_key[:60])])
    return InlineKeyboardMarkup(keyboard_buttons) if keyboard_buttons else None


def get_player_selection_keyboard(action_prefix: str,
                                  include_status_type: str | None = "activation") -> InlineKeyboardMarkup | None:
    buttons = []
    if not player_data:
        return None
    sorted_players = sorted(player_data.items(), key=lambda item: item[1].get('character_name', ''))
    for pid_int, p_info in sorted_players:
        pid = int(pid_int)
        name = p_info.get('character_name', f"Player {pid}")
        button_text = f"{name} (ID: {pid})"
        if include_status_type == "activation":
            status_text = "Active" if p_info.get('is_active') else "Inactive"
            button_text += f" - {status_text}"
        elif include_status_type == "game_status":
            current_player_status = p_info.get('status', STATUS_UNDEFINED)
            button_text += f" - Status: {current_player_status}"
        elif include_status_type == "secret_mission":
            current_secret_id = p_info.get("secret_mission_id")
            if current_secret_id and current_secret_id in secret_missions_data:
                button_text += f" (SM: {secret_missions_data[current_secret_id].get('title', current_secret_id)[:10]}...)"
            elif current_secret_id:
                button_text += f" (SM: ID {current_secret_id})"
        callback_data = f"{action_prefix}_{pid}"
        if len(callback_data) > 60:
            logger.warning(f"Callback data for player {pid} too long for action {action_prefix}, might be truncated.")
        buttons.append([InlineKeyboardButton(button_text, callback_data=callback_data[:60])])
    buttons.append([InlineKeyboardButton("Cancel Action", callback_data=f"{action_prefix}_cancel")])
    return InlineKeyboardMarkup(buttons) if buttons else None


def get_status_selection_keyboard(player_id: int) -> InlineKeyboardMarkup:
    buttons = []
    for status_val in VALID_PLAYER_STATUSES:
        encoded_status = status_val.replace('(', '').replace(')', '').replace(' ', '_').lower()
        buttons.append([InlineKeyboardButton(status_val, callback_data=f"setstatus_{player_id}_{encoded_status}")])
    buttons.append([InlineKeyboardButton("Cancel Status Change", callback_data=f"setstatus_{player_id}_cancel")])
    return InlineKeyboardMarkup(buttons)


def get_secret_mission_selection_keyboard(player_id: int) -> InlineKeyboardMarkup | None:
    buttons = []
    if not secret_missions_data:
        buttons.append([InlineKeyboardButton("No secret missions defined.", callback_data="secretmission_none")])
    else:
        for sm_id, sm_data in secret_missions_data.items():
            title = sm_data.get("title", f"Mission {sm_id}")
            callback_data = f"secretmission_set_{player_id}_{sm_id}"
            if len(callback_data) > 60:
                logger.warning(f"Callback data for secret mission {sm_id} too long, might be truncated.")
            buttons.append([InlineKeyboardButton(title[:40], callback_data=callback_data[:60])])
    buttons.append([InlineKeyboardButton("--- Clear Secret Mission for Player ---",
                                         callback_data=f"secretmission_set_{player_id}_clear")])
    buttons.append([InlineKeyboardButton("Cancel", callback_data=f"secretmission_set_{player_id}_cancel_selection")])
    return InlineKeyboardMarkup(buttons)


def get_broadcast_target_keyboard() -> InlineKeyboardMarkup:
    keyboard = [[InlineKeyboardButton("All Players", callback_data="broadcast_target_all")],
                [InlineKeyboardButton("Active Players Only", callback_data="broadcast_target_active")],
                [InlineKeyboardButton("Inactive Players Only", callback_data="broadcast_target_inactive")],
                [InlineKeyboardButton("Cancel Broadcast", callback_data="broadcast_cancel")]]
    return InlineKeyboardMarkup(keyboard)


def get_confirmation_keyboard(yes_callback: str, no_callback: str) -> InlineKeyboardMarkup:
    keyboard = [[InlineKeyboardButton("Yes, proceed", callback_data=yes_callback)],
                [InlineKeyboardButton("No, cancel", callback_data=no_callback)]]
    return InlineKeyboardMarkup(keyboard)


def get_recipient_choice_keyboard(sender_id: int) -> ReplyKeyboardMarkup | None:
    all_recipients = list(message_recipients)

    player_names = [p_info.get("character_name", f"Player {pid}") for pid, p_info in player_data.items() if
                    pid != sender_id and p_info.get("is_active")]
    all_recipients.extend(player_names)

    if not all_recipients: return None

    # Sort recipients alphabetically for better UX
    all_recipients.sort()

    keyboard = [[name] for name in all_recipients]
    keyboard.append(["Back"])
    return ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)


def get_remove_keyboard() -> ReplyKeyboardRemove:
    return ReplyKeyboardRemove()


# --- PLAYER COMMAND HANDLERS ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global WELCOME_IMAGE_FILE_ID
    user = update.effective_user
    user_id = user.id
    if user_id not in player_data:
        player_data[user_id] = {
            "telegram_user_id": user_id,
            "character_name": f"New Player {user.first_name}",
            "character_role": "Undefined",
            "character_bio": "No information.",
            "character_image_url": None,
            "character_image_file_id": None,  # NEW: Field for caching file_id
            "is_active": False,
            "status": STATUS_UNDEFINED,
            "secret_mission_id": None,
            "current_mission_id": "default_mission"
        }
        if "default_mission" not in missions_data:
            missions_data["default_mission"] = {
                "title": "Awaiting Instructions",
                "description": "Your mission has not been determined yet.",
                "objectives": []
            }
            save_missions_data()
        save_player_data()
        logger.info(f"New player registered (inactive, status: {STATUS_UNDEFINED}): {user_id} - {user.first_name}")
        await context.bot.send_message(
            chat_id=DM_CHAT_ID,
            text=f"New player registered: {user.first_name} (ID: {user_id}, @{user.username or 'N/A'}).\n"
                 f"Status: {STATUS_UNDEFINED}. Awaiting activation. Use Admin Panel."
        )
        image_url = "./assets/character/lore/bg.png"
        caption_text = "Welcome! Your account is created and awaits activation."

        # MODIFIED: Use file_id for welcome image to speed up loading
        photo_to_send = WELCOME_IMAGE_FILE_ID
        if not photo_to_send and os.path.exists(image_url):
            photo_to_send = open(image_url, 'rb')

        if photo_to_send:
            try:
                sent_message = await update.message.reply_photo(
                    photo=photo_to_send,
                    caption=caption_text
                )
                # Cache the file_id if it wasn't already
                if not WELCOME_IMAGE_FILE_ID and sent_message.photo:
                    WELCOME_IMAGE_FILE_ID = sent_message.photo[-1].file_id
                    logger.info(f"Cached welcome image file_id: {WELCOME_IMAGE_FILE_ID}")
            except Exception as e:
                logger.error(f"Failed to send start command photo: {e}")
                await update.message.reply_text(caption_text)
        else:
            await update.message.reply_text(caption_text)
        return

    markup = get_main_reply_keyboard(user_id)
    await update.message.reply_html(rf"Hello, {user.mention_html()}! Welcome to Eventide: Eclipse.",
                                    reply_markup=markup)


async def lore_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if not is_admin(user_id) and not is_player_active(user_id):
        await update.message.reply_text("Your account is awaiting activation for the mission.")
        return
    if "error" in lore_data:
        await update.message.reply_text(lore_data["error"])
        return
    reply_markup = get_lore_main_menu_keyboard()
    if reply_markup:
        await update.message.reply_text('Select a section to study:', reply_markup=reply_markup)
    else:
        await update.message.reply_text("Lore sections not found or configured incorrectly.")


async def lore_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user_id = query.from_user.id
    if not is_admin(user_id) and not is_player_active(user_id):
        await query.answer("Your account is awaiting activation by the Game Master.", show_alert=True)
        return
    await query.answer()
    callback_path_str = query.data[len("lore_"):]
    path_keys = callback_path_str.split("_sections_")

    current_level = lore_data
    # This list will store references to the dictionaries in the path to allow modification
    path_objects = [lore_data]

    navigated_successfully = True
    for i, key in enumerate(path_keys):
        if isinstance(current_level, dict) and key in current_level:
            current_level = current_level[key]
            path_objects.append(current_level)
            if i < len(path_keys) - 1:
                if "sections" in current_level and isinstance(current_level.get("sections"), dict):
                    current_level = current_level["sections"]
                    path_objects.append(current_level)
                else:
                    logger.warning(f"Expected 'sections' dict under key '{key}'. Callback: '{query.data}'.")
                    navigated_successfully = False;
                    break
        else:
            # Handle case for top-level string like 'introduction'
            if i == 0 and isinstance(lore_data.get(key), str):
                current_level = lore_data[key]
                path_objects.append(current_level)
            else:
                logger.warning(f"Key '{key}' not found in path. Full Callback: '{query.data}'.")
                navigated_successfully = False
            break

    if not navigated_successfully:
        if query.message: await query.edit_message_text(text="Error navigating lore data. Please try /lore again.")
        return

    text_content = "Information not found."
    keyboard_buttons = []

    # NEW: The dictionary that contains the image info, for caching.
    image_container = None

    if len(path_keys) == 1:
        parent_callback_data = "lore_main_menu_trigger"
    else:
        parent_callback_data = "lore_" + "_sections_".join(path_keys[:-1])

    keyboard_buttons.append([InlineKeyboardButton("⬅️ Back", callback_data=parent_callback_data)])

    if isinstance(current_level, str):
        text_content = current_level
        # The container for intro image is the main lore_data dict
        if path_keys and len(path_keys) == 1 and path_keys[0] == "introduction":
            image_container = lore_data
    elif isinstance(current_level, dict):
        image_container = current_level
        text_content = current_level.get("description") or current_level.get("text") or current_level.get("title",
                                                                                                          "Select a subsection:")

        if "sections" in current_level and isinstance(current_level.get("sections"), dict):
            for section_key, section_item in current_level["sections"].items():
                title = section_item.get("title", section_key.replace("_", " ").capitalize())
                section_cb_data = f"lore_{callback_path_str}_sections_{section_key}"
                if len(section_cb_data) > 60:
                    section_cb_data = section_cb_data[:60]
                keyboard_buttons.append([InlineKeyboardButton(title, callback_data=section_cb_data)])

    keyboard_markup = InlineKeyboardMarkup(keyboard_buttons)
    if isinstance(text_content, str):
        text_content = text_content.replace("<br><br>", "\n\n").replace("<br>", "\n")

    if not query.message: return

    try:
        # MODIFIED: Logic to send photo with caching
        has_photo_info = image_container and ("image_url" in image_container or "image_file_id" in image_container)

        # Delete the old message and send a new one to avoid "Message is not modified" error
        # when only the image changes or appears/disappears.
        await query.message.delete()

        sent_message: Message | None = None

        if has_photo_info:
            file_id = image_container.get("image_file_id")
            image_url = image_container.get("image_url")

            photo_to_send = file_id
            if not photo_to_send:
                if image_url.startswith("./") or not image_url.startswith("http"):
                    image_path = os.path.join(BASE_DIR, image_url.lstrip("./"))
                    if os.path.exists(image_path):
                        photo_to_send = open(image_path, 'rb')
                else:  # It's a public URL
                    photo_to_send = image_url

            if photo_to_send:
                try:
                    sent_message = await context.bot.send_photo(
                        chat_id=query.message.chat_id,
                        photo=photo_to_send
                    )
                    # NEW: Cache the file_id if it's the first time
                    if not file_id and sent_message and sent_message.photo:
                        image_container["image_file_id"] = sent_message.photo[-1].file_id
                        logger.info(f"Cached lore image file_id for path: {callback_path_str}")
                        save_lore_data()
                except Exception as e_photo:
                    logger.error(f"Failed to send lore photo {image_url}: {e_photo}")

        # Send the text content as a new message, with keyboard
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=text_content,
            reply_markup=keyboard_markup,
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        logger.error(f"Error in lore_callback: {e}. Path: {query.data}")
        try:
            # Send as a new message since the old one was deleted
            await context.bot.send_message(query.message.chat_id, "An error occurred. Try /lore again.")
        except Exception as e2:
            logger.error(f"Error sending fallback in lore_callback: {e2}")


async def lore_main_menu_trigger_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    if not is_admin(user_id) and not is_player_active(user_id):
        await query.answer("Your account is awaiting activation.", show_alert=True)
        return
    await query.answer()
    reply_markup = get_lore_main_menu_keyboard()
    if reply_markup and query.message:
        try:
            await query.edit_message_text('Select a section to study:', reply_markup=reply_markup)
        except Exception as e:
            logger.error(f"Error editing message in lore_main_menu_trigger_callback: {e}")
            # Fallback if editing fails
            await query.message.reply_text('Select a section to study:', reply_markup=reply_markup)
    elif query.message:
        await query.edit_message_text("Lore sections not found.")


async def character_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if not is_admin(user_id) and not is_player_active(user_id):
        await update.message.reply_text("Your account is awaiting activation by the Game Master.")
        return
    if user_id in player_data:
        char = player_data[user_id]

        caption = (f"👤 **Name:** {char.get('character_name', 'Undefined')}\n"
                   f"🛠️ **Role:** {char.get('character_role', 'Undefined')}\n"
                   f"📝 **Bio:** {char.get('character_bio', 'No information.')}\n"
                   f"🚦 **Ver:** {char.get('ver', '1.0.0')}\n")
        secret_mission_id = char.get("secret_mission_id")
        if secret_mission_id and secret_mission_id in secret_missions_data:
            sm = secret_missions_data[secret_mission_id]
            caption += f"\n🔒 **Secret Mission:** {sm.get('title', 'N/A')}\n"
            if sm.get('details'):
                caption += f"    **Details:** {sm.get('details')}\n"
        elif secret_mission_id:
            caption += f"\n🔒 **Secret Mission ID:** {secret_mission_id} (Details not found)\n"

        # MODIFIED: Photo sending logic with caching
        char_image_file_id = char.get("character_image_file_id")
        char_image_url = char.get("character_image_url")

        photo_to_send = char_image_file_id
        if not photo_to_send and char_image_url:
            if char_image_url.startswith("./") or not char_image_url.startswith("http"):
                image_path = os.path.join(BASE_DIR, char_image_url.lstrip("./"))
                if os.path.exists(image_path):
                    photo_to_send = open(image_path, 'rb')
            else:
                photo_to_send = char_image_url

        if photo_to_send:
            try:
                sent_message = await update.message.reply_photo(
                    photo=photo_to_send,
                    caption=caption,
                    parse_mode=ParseMode.MARKDOWN
                )
                # NEW: Cache the file_id if it wasn't already
                if not char_image_file_id and sent_message and sent_message.photo:
                    player_data[user_id]["character_image_file_id"] = sent_message.photo[-1].file_id
                    logger.info(f"Cached character image file_id for player {user_id}")
                    save_player_data()
            except Exception as e:
                logger.error(f"Failed to send character photo for {user_id}: {e}")
                await update.message.reply_text(caption, parse_mode=ParseMode.MARKDOWN)
        else:
            await update.message.reply_text(caption, parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text("Your character information not found. Try /start to register.")


async def mission_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if not is_admin(user_id) and not is_player_active(user_id):
        await update.message.reply_text("Your account is awaiting activation by the Game Master.")
        return
    if user_id in player_data:
        mission_id = player_data[user_id].get("current_mission_id")
        if mission_id and mission_id in missions_data:
            mission = missions_data[mission_id]
            objectives_text = "\n".join([f"- {obj}" for obj in mission.get('objectives', [])])
            text = (f"🎯 **Mission:** {mission.get('title', 'Untitled')}\n\n"
                    f"📜 **Description:**\n{mission.get('description', 'No description.')}\n\n"
                    f"📋 **Objectives:**\n{objectives_text if objectives_text else 'Objectives are not defined.'}")
            await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
        else:
            await update.message.reply_text("Your current mission is not found or not defined.")
    else:
        await update.message.reply_text("Your character information not found. Try /start to register.")


async def send_message_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    if not is_admin(user_id) and not is_player_active(user_id):
        await update.message.reply_text("Your account is awaiting activation by the Game Master.")
        return ConversationHandler.END
    reply_markup = get_recipient_choice_keyboard(user_id)
    if not reply_markup:
        await update.message.reply_text("There is no one available to send a message to.")
        markup_main = get_main_reply_keyboard(user_id)
        await update.message.reply_text("Returning to main menu.", reply_markup=markup_main)
        return ConversationHandler.END
    await update.message.reply_text("Who do you want to send a message to? Choose from the list or select 'Back'.",
                                    reply_markup=reply_markup)
    return CHOOSE_RECIPIENT


async def choose_recipient(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    recipient_name = update.message.text
    markup_main = get_main_reply_keyboard(update.effective_user.id)
    if recipient_name.lower() == "back":
        await update.message.reply_text("Message sending cancelled.", reply_markup=markup_main)
        return ConversationHandler.END

    target_player_id = None
    for pid, p_info in player_data.items():
        if p_info.get("character_name") == recipient_name:
            target_player_id = pid
            break

    if target_player_id:
        context.user_data['recipient'] = {"name": recipient_name, "type": "player", "id": target_player_id}
    elif recipient_name in message_recipients:
        context.user_data['recipient'] = {"name": recipient_name, "type": "npc", "id": None}
    else:
        reply_markup_retry = get_recipient_choice_keyboard(update.effective_user.id)
        await update.message.reply_text("Recipient not found. Please choose from the provided list or select 'Back'.",
                                        reply_markup=reply_markup_retry)
        return CHOOSE_RECIPIENT

    await update.message.reply_text(f"Selected: {recipient_name}. Now, please enter your message.",
                                    reply_markup=get_remove_keyboard())
    return TYPE_MESSAGE


async def type_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    message_text = update.message.text
    recipient_info = context.user_data.get('recipient')
    sender = update.effective_user
    sender_id = sender.id
    markup_main = get_main_reply_keyboard(sender_id)
    player_current_status = get_player_status(sender_id)

    sender_char_name = player_data.get(sender_id, {}).get('character_name', sender.first_name)

    if not recipient_info:
        await update.message.reply_text("Error: Recipient not selected. Please start again.", reply_markup=markup_main)
        return ConversationHandler.END

    recipient_name = recipient_info["name"]
    recipient_type = recipient_info["type"]
    recipient_id = recipient_info["id"]

    dm_notification_prefix = f"--- Msg from {sender_char_name}(ID:{sender_id},Status:{player_current_status}) to {recipient_name} ---\n"
    player_feedback_message = "Message delivered. Please wait for a response."

    if player_current_status == STATUS_ARRESTED:
        await context.bot.send_message(DM_CHAT_ID,
                                       f"ELLI ALERT: Arrested {sender_char_name}(ID:{sender_id}) attempted comm.\nTo:{recipient_name}\nMsg:{message_text}")
        await update.message.reply_text(
            "You are under arrest. All communication attempts are being monitored by ELLI. Await further instructions.",
            reply_markup=markup_main)
    elif player_current_status == STATUS_HACKED:
        await context.bot.send_message(DM_CHAT_ID,
                                       f"TECHNOCRAT ALERT: Hacked {sender_char_name}(ID:{sender_id}) sent.\nOriginal To:{recipient_name}\nIntercepted:{message_text}")
        await update.message.reply_text("Message sent - wait.",
                                        reply_markup=markup_main)
    elif player_current_status == STATUS_DEAD:
        await context.bot.send_message(DM_CHAT_ID,
                                       f"INFO: DEAD Player {sender_char_name}(ID:{sender_id}) tried to send to {recipient_name}: {message_text}")
        await update.message.reply_text("No response... silence on the airwaves...", reply_markup=markup_main)
    else:
        try:
            await context.bot.send_message(chat_id=DM_CHAT_ID,
                                           text=dm_notification_prefix + f"Message:\n{message_text}")
        except Exception as e:
            logger.error(f"Error sending message to DM: {e}")
            player_feedback_message = "Failed to send the message to the Game Master. Please try again later."
            await update.message.reply_text(player_feedback_message, reply_markup=markup_main)
            if 'recipient' in context.user_data: del context.user_data['recipient']
            return ConversationHandler.END

        if recipient_type == "player" and recipient_id:
            try:
                player_to_player_message = f"Message from **{sender_char_name}**:\n\n{message_text}"
                await context.bot.send_message(chat_id=recipient_id, text=player_to_player_message,
                                               parse_mode=ParseMode.MARKDOWN)
            except Exception as e:
                logger.error(f"Failed to forward message to player {recipient_id}: {e}")
                player_feedback_message = "The message was delivered to the Game Master, but could not be delivered to the player."

        await update.message.reply_text(player_feedback_message, reply_markup=markup_main)

    if 'recipient' in context.user_data: del context.user_data['recipient']
    return ConversationHandler.END


async def cancel_send_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    markup_main = get_main_reply_keyboard(update.effective_user.id)
    await update.message.reply_text("Message sending cancelled.", reply_markup=markup_main)
    if 'recipient' in context.user_data: del context.user_data['recipient']
    return ConversationHandler.END


# --- ADMIN COMMAND HANDLERS ---
async def admin_panel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update.effective_user.id): await update.message.reply_text(
        "This command is for administrators only."); return
    await update.message.reply_text("Admin Panel:", reply_markup=get_admin_panel_keyboard())


async def back_to_main_menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Returning to main menu...",
                                    reply_markup=get_main_reply_keyboard(update.effective_user.id))


async def ask_player_for_action(update: Update, context: ContextTypes.DEFAULT_TYPE, action: str) -> int:
    if not is_admin(update.effective_user.id): await update.message.reply_text(
        "No permission."); return ConversationHandler.END
    context.user_data['admin_action'] = action
    keyboard = get_player_selection_keyboard(action_prefix=action, include_status_type="activation")
    if not keyboard: await update.message.reply_text("No players found."); return ConversationHandler.END
    action_text = "activate" if action == "activate" else "deactivate"
    await update.message.reply_text(f"Select player to {action_text}:", reply_markup=keyboard)
    return SELECT_PLAYER_FOR_ACTION


async def admin_activate_player_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    return await ask_player_for_action(update, context, "activate")


async def admin_deactivate_player_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    return await ask_player_for_action(update, context, "deactivate")


async def process_player_action_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query;
    await query.answer()
    action_type_from_cb = query.data.split("_")[0]
    admin_markup = get_admin_panel_keyboard()
    if query.data.endswith("_cancel"):
        await query.edit_message_text("Action cancelled.")
        await query.message.reply_text("Admin Panel:", reply_markup=admin_markup);
        return ConversationHandler.END
    try:
        player_id = int(query.data.split("_")[-1])
    except (IndexError, ValueError):
        await query.edit_message_text("Invalid selection.");
        return SELECT_PLAYER_FOR_ACTION
    action = context.user_data.get('admin_action')
    if not action or action != action_type_from_cb:
        logger.error(f"Action mismatch: expected {action}, got {action_type_from_cb}")
        await query.edit_message_text("Action mismatch. Start over.")
        await query.message.reply_text("Admin Panel:", reply_markup=admin_markup);
        return ConversationHandler.END
    if player_id in player_data:
        p_info = player_data[player_id];
        p_name = p_info.get('character_name', player_id)
        if action == "activate":
            if not p_info.get("is_active"):
                p_info["is_active"] = True;
                msg = f"Player {p_name} activated."
            else:
                msg = f"Player {p_name} already active."
        elif action == "deactivate":
            if p_info.get("is_active"):
                p_info["is_active"] = False;
                msg = f"Player {p_name} deactivated."
            else:
                msg = f"Player {p_name} already inactive."
        if save_player_data():
            await query.edit_message_text(msg)
            if action == "activate" and msg.endswith("activated."):
                await context.bot.send_message(player_id,
                                               "You have been activated for the mission. Godspeed, and may you serve the Earth Federation with honor! You can now use all comlog commands.")
            elif action == "deactivate" and msg.endswith("deactivated."):
                await context.bot.send_message(player_id, "Your account has been deactivated by the Game Master. Thank you for a game!")
        else:
            await query.edit_message_text("Error saving data.")
    else:
        await query.edit_message_text(f"Player ID {player_id} not found.")
    await query.message.reply_text("Admin Panel:", reply_markup=admin_markup);
    return ConversationHandler.END


async def cancel_admin_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query;
    msg_obj = query.message if query else update.message
    if query:
        await query.answer();
        await query.edit_message_text("Action cancelled.")
    else:
        await update.message.reply_text("Action cancelled.")
    await msg_obj.reply_text("Admin Panel:", reply_markup=get_admin_panel_keyboard());
    return ConversationHandler.END


async def admin_set_player_status_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not is_admin(update.effective_user.id): await update.message.reply_text(
        "No permission."); return ConversationHandler.END
    keyboard = get_player_selection_keyboard(action_prefix="setstatus", include_status_type="game_status")
    if not keyboard: await update.message.reply_text("No players found."); return ConversationHandler.END
    await update.message.reply_text("Select player to set status:", reply_markup=keyboard);
    return SELECT_PLAYER_FOR_STATUS


async def set_player_status_select_player(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query;
    await query.answer()
    if query.data.endswith("_cancel"): await query.edit_message_text(
        "Set status cancelled."); await query.message.reply_text("Admin Panel:",
                                                                 reply_markup=get_admin_panel_keyboard()); return ConversationHandler.END
    try:
        player_id = int(query.data.split("_")[-1])
    except (IndexError, ValueError):
        await query.edit_message_text("Invalid selection.");
        return SELECT_PLAYER_FOR_STATUS
    if player_id not in player_data: await query.edit_message_text("Player not found."); return SELECT_PLAYER_FOR_STATUS
    context.user_data['status_target_player_id'] = player_id
    p_name = player_data[player_id].get('character_name', player_id);
    current_status = player_data[player_id].get('status', STATUS_UNDEFINED)
    status_kb = get_status_selection_keyboard(player_id)
    await query.edit_message_text(f"Player: {p_name}. Current status: {current_status}.\nSelect new status:",
                                  reply_markup=status_kb)
    return SELECT_NEW_STATUS


async def set_player_status_select_new_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query;
    await query.answer()
    admin_markup = get_admin_panel_keyboard()
    player_id = context.user_data.get('status_target_player_id')
    if not player_id or player_id not in player_data:
        await query.edit_message_text("Error: Player ID missing. Start over.");
        await query.message.reply_text("Admin Panel:", reply_markup=admin_markup);
        return ConversationHandler.END
    if query.data.endswith("_cancel"):
        await query.edit_message_text("Set status cancelled.");
        await query.message.reply_text("Admin Panel:", reply_markup=admin_markup);
        return ConversationHandler.END
    try:
        parts = query.data.split("_");
        new_status_encoded = "_".join(parts[2:])
        selected_status = None
        for s_val in VALID_PLAYER_STATUSES:
            encoded_valid_s = s_val.replace('(', '').replace(')', '').replace(' ', '_').lower()
            if encoded_valid_s == new_status_encoded:
                selected_status = s_val;
                break
        if not selected_status:
            logger.error(f"Invalid status encoding '{new_status_encoded}' from callback '{query.data}'.")
            await query.edit_message_text("Invalid status selected. Please try again.");
            return SELECT_NEW_STATUS
    except (IndexError, ValueError) as e:
        logger.error(f"Error parsing status from cb: {query.data} - {e}")
        await query.edit_message_text("Error processing. Start over.");
        await query.message.reply_text("Admin Panel:", reply_markup=admin_markup);
        return ConversationHandler.END

    player_data[player_id]["status"] = selected_status
    if save_player_data():
        p_name = player_data[player_id].get('character_name', player_id)
        await query.edit_message_text(f"Status for {p_name} (ID: {player_id}) set to: {selected_status}.")
        # try:
        #     await context.bot.send_message(player_id,
        #                                    f"A Game Master has updated your status to: **{selected_status}**.",
        #                                    parse_mode=ParseMode.MARKDOWN)
        # except Exception as e:
        #     logger.warning(f"Failed to notify player {player_id} of status change: {e}")
    else:
        await query.edit_message_text("Error saving status.")
    await query.message.reply_text("Admin Panel:", reply_markup=admin_markup)
    if 'status_target_player_id' in context.user_data: del context.user_data['status_target_player_id']
    return ConversationHandler.END


async def cancel_set_player_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query;
    msg_obj = query.message if query else update.message
    if query:
        await query.answer();
        await query.edit_message_text("Set status cancelled.")
    else:
        await update.message.reply_text("Set status cancelled.")
    await msg_obj.reply_text("Admin Panel:", reply_markup=get_admin_panel_keyboard())
    if 'status_target_player_id' in context.user_data: del context.user_data['status_target_player_id']
    return ConversationHandler.END


# --- Admin Set Secret Mission Conversation ---
async def admin_set_secret_mission_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not is_admin(update.effective_user.id): await update.message.reply_text(
        "No permission."); return ConversationHandler.END
    keyboard = get_player_selection_keyboard(action_prefix="secretmission", include_status_type="secret_mission")
    if not keyboard: await update.message.reply_text("No players found."); return ConversationHandler.END
    await update.message.reply_text("Select player for secret mission:", reply_markup=keyboard);
    return SELECT_PLAYER_FOR_SECRET_MISSION


async def secret_mission_select_player(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query;
    await query.answer()
    if query.data.endswith("_cancel"):
        await query.edit_message_text("Set secret mission cancelled.");
        await query.message.reply_text("Admin Panel:", reply_markup=get_admin_panel_keyboard());
        return ConversationHandler.END
    try:
        player_id = int(query.data.split("_")[-1])
    except (IndexError, ValueError):
        await query.edit_message_text("Invalid selection.");
        return SELECT_PLAYER_FOR_SECRET_MISSION
    if player_id not in player_data: await query.edit_message_text(
        "Player not found."); return SELECT_PLAYER_FOR_SECRET_MISSION
    context.user_data['secret_mission_player_id'] = player_id
    p_name = player_data[player_id].get('character_name', player_id)

    secret_mission_kb = get_secret_mission_selection_keyboard(player_id)
    current_sm_id = player_data[player_id].get("secret_mission_id")
    current_sm_title = secret_missions_data.get(current_sm_id, {}).get("title", "None") if current_sm_id else "None"

    await query.edit_message_text(
        f"Player: {p_name}. Current secret mission: {current_sm_title}.\nSelect new secret mission:",
        reply_markup=secret_mission_kb)
    return CHOOSE_SECRET_MISSION


async def secret_mission_choose_mission(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query;
    await query.answer()
    admin_markup = get_admin_panel_keyboard()
    player_id = context.user_data.get('secret_mission_player_id')

    if not player_id or player_id not in player_data:
        await query.edit_message_text("Error: Player context lost. Start over.");
        await query.message.reply_text("Admin Panel:", reply_markup=admin_markup);
        return ConversationHandler.END

    if query.data.endswith("_cancel_selection"):
        await query.edit_message_text("Set secret mission cancelled.");
        await query.message.reply_text("Admin Panel:", reply_markup=admin_markup);
        return ConversationHandler.END
    if query.data == "secretmission_none":
        await query.edit_message_text("No secret missions defined. Action cancelled.");
        await query.message.reply_text("Admin Panel:", reply_markup=admin_markup);
        return ConversationHandler.END

    try:
        parts = query.data.split("_")
        action_player_id = int(parts[2])
        mission_id_to_set = "_".join(parts[3:]) if len(parts) > 3 else "clear"

        if len(parts) > 3 and parts[3] == "clear":
            mission_id_to_set = "clear"

        if action_player_id != player_id:
            await query.edit_message_text("Player ID mismatch. Start over.");
            await query.message.reply_text("Admin Panel:", reply_markup=admin_markup);
            return ConversationHandler.END

        p_name = player_data[player_id].get('character_name', player_id)
        if mission_id_to_set == "clear":
            player_data[player_id]['secret_mission_id'] = None
            if save_player_data():
                await query.edit_message_text(f"Secret mission cleared for {p_name}.")
                try:
                    await context.bot.send_message(player_id,
                                                   "Your secret mission has been cleared by the Game Master.")
                except Exception as e:
                    logger.warning(f"Failed to notify player {player_id} of secret mission clearance: {e}")
            else:
                await query.edit_message_text("Error saving player data.")
        elif mission_id_to_set and mission_id_to_set in secret_missions_data:
            player_data[player_id]['secret_mission_id'] = mission_id_to_set
            if save_player_data():
                sm_title = secret_missions_data[mission_id_to_set].get("title", mission_id_to_set)
                await query.edit_message_text(f"Secret mission '{sm_title}' set for {p_name}.")
                try:
                    await context.bot.send_message(player_id,
                                                   f"You have a new secret mission: **{sm_title}**. Check `/character` for details.",
                                                   parse_mode=ParseMode.MARKDOWN)
                except Exception as e:
                    logger.warning(f"Failed to notify player {player_id} of new secret mission: {e}")
            else:
                await query.edit_message_text("Error saving player data.")
        else:
            await query.edit_message_text(f"Invalid secret mission ID: {mission_id_to_set}. Please try again.")
            kb = get_secret_mission_selection_keyboard(player_id)
            if kb: await query.message.reply_text("Select new secret mission:", reply_markup=kb);
            return CHOOSE_SECRET_MISSION
    except Exception as e:
        logger.error(f"Error processing secret mission selection: {e}. Data: {query.data}")
        await query.edit_message_text("Error setting secret mission. Start over.");

    await query.message.reply_text("Admin Panel:", reply_markup=admin_markup)
    if 'secret_mission_player_id' in context.user_data: del context.user_data['secret_mission_player_id']
    return ConversationHandler.END


# --- Admin Broadcast, Direct Message, List Players, Update Mission/Character/Recipients functions ---
async def admin_broadcast_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not is_admin(update.effective_user.id): await update.message.reply_text(
        "No permission."); return ConversationHandler.END
    await update.message.reply_text("Choose broadcast target:", reply_markup=get_broadcast_target_keyboard());
    return CHOOSE_BROADCAST_TARGET


async def broadcast_choose_target(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query;
    await query.answer();
    target = query.data.split("_")[-1]
    if target == "cancel": await query.edit_message_text("Broadcast cancelled."); await query.message.reply_text(
        "Admin Panel:", reply_markup=get_admin_panel_keyboard()); return ConversationHandler.END
    context.user_data['broadcast_target'] = target
    await query.edit_message_text("Enter sender name (or 'default' for Game Master):");
    return TYPE_BROADCAST_SENDER_NAME


async def broadcast_type_sender(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    sender_name = update.message.text
    context.user_data['broadcast_sender'] = "Game Master" if sender_name.lower() == 'default' else sender_name
    await update.message.reply_text("Enter broadcast message text:");
    return TYPE_BROADCAST_MESSAGE_TEXT


async def broadcast_type_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['broadcast_message'] = update.message.text
    sender = context.user_data['broadcast_sender'];
    target_map = {"all": "All", "active": "Active", "inactive": "Inactive"}
    target_disp = target_map.get(context.user_data['broadcast_target'], "Unknown")
    preview = f"--PREVIEW--\nFrom: {sender}\nTo: {target_disp} Players\n\n{context.user_data['broadcast_message']}\n\nConfirm send?"
    await update.message.reply_text(preview, reply_markup=get_confirmation_keyboard("broadcast_confirm_yes",
                                                                                    "broadcast_confirm_no"));
    return CONFIRM_BROADCAST_SEND


async def broadcast_confirm_send(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query;
    await query.answer();
    admin_markup = get_admin_panel_keyboard()
    if query.data == "broadcast_confirm_no":
        await query.edit_message_text("Broadcast cancelled.");
        await query.message.reply_text("Admin Panel:", reply_markup=admin_markup);
        return ConversationHandler.END
    target = context.user_data.get('broadcast_target');
    sender = context.user_data.get('broadcast_sender');
    msg_txt = context.user_data.get('broadcast_message')
    if not all([target, sender, msg_txt]):
        await query.edit_message_text("Error: Broadcast data missing. Start over.");
        await query.message.reply_text("Admin Panel:", reply_markup=admin_markup);
        return ConversationHandler.END
    rec_ids = [pid for pid, p in player_data.items() if (
            target == "all" or (target == "active" and p.get("is_active")) or (
            target == "inactive" and not p.get("is_active")))]
    count = 0;
    final_msg = f"📢 **{sender}:**\n\n{msg_txt}"
    for pid in rec_ids:
        try:
            await context.bot.send_message(pid, final_msg, parse_mode=ParseMode.MARKDOWN);
            count += 1
        except Exception as e:
            logger.error(f"Failed broadcast to {pid}: {e}")
    await query.edit_message_text(f"Broadcast sent to {count} players.");
    await query.message.reply_text("Admin Panel:", reply_markup=admin_markup)
    for k in ['broadcast_target', 'broadcast_sender', 'broadcast_message']: context.user_data.pop(k, None)
    return ConversationHandler.END


async def broadcast_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query;
    msg_obj = query.message if query else update.message
    if query:
        await query.answer();
        if query.message: await query.edit_message_text("Broadcast cancelled.")
    else:
        await update.message.reply_text("Broadcast cancelled.")

    await msg_obj.reply_text("Admin Panel:", reply_markup=get_admin_panel_keyboard())
    for k in ['broadcast_target', 'broadcast_sender', 'broadcast_message']: context.user_data.pop(k, None)
    return ConversationHandler.END


async def admin_direct_message_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not is_admin(update.effective_user.id): await update.message.reply_text(
        "No permission."); return ConversationHandler.END
    keyboard = get_player_selection_keyboard("dmselect", include_status_type=None);
    if not keyboard: await update.message.reply_text("No players found."); return ConversationHandler.END
    await update.message.reply_text("Select player for direct message:", reply_markup=keyboard);
    return SELECT_DM_PLAYER


async def direct_message_select_player(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query;
    await query.answer()
    if query.data.endswith("_cancel"): await query.edit_message_text("DM cancelled."); await query.message.reply_text(
        "Admin Panel:", reply_markup=get_admin_panel_keyboard()); return ConversationHandler.END
    try:
        player_id = int(query.data.split("_")[-1])
    except (IndexError, ValueError):
        await query.edit_message_text("Invalid selection.");
        return SELECT_DM_PLAYER
    if player_id not in player_data: await query.edit_message_text("Player not found."); return SELECT_DM_PLAYER
    context.user_data['dm_target_player_id'] = player_id
    p_name = player_data[player_id].get('character_name', player_id)
    await query.edit_message_text(f"To: {p_name}.\nEnter sender name (or 'default' for Game Master):");
    return TYPE_DM_SENDER_NAME


async def direct_message_type_sender_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    sender_name = update.message.text
    context.user_data['dm_sender_name'] = "Game Master" if sender_name.lower() == 'default' else sender_name
    await update.message.reply_text("Enter message text:");
    return TYPE_DM_MESSAGE_TEXT


async def direct_message_type_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['dm_message_text'] = update.message.text
    pid = context.user_data['dm_target_player_id'];
    p_name = player_data.get(pid, {}).get('character_name', pid);
    sender = context.user_data['dm_sender_name']
    preview = f"--PREVIEW DM--\nTo: {p_name}\nFrom: {sender}\n\n{context.user_data['dm_message_text']}\n\nConfirm?"
    await update.message.reply_text(preview, reply_markup=get_confirmation_keyboard("dm_confirm_yes", "dm_confirm_no"));
    return CONFIRM_DM_SEND


async def direct_message_confirm_send(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query;
    await query.answer();
    admin_markup = get_admin_panel_keyboard()
    if query.data == "dm_confirm_no": await query.edit_message_text("DM cancelled."); await query.message.reply_text(
        "Admin Panel:", reply_markup=admin_markup); return ConversationHandler.END
    pid = context.user_data.get('dm_target_player_id');
    sender = context.user_data.get('dm_sender_name');
    msg_txt = context.user_data.get('dm_message_text')
    if not all([pid, sender, msg_txt]): await query.edit_message_text(
        "Error: DM data missing."); await query.message.reply_text("Admin Panel:",
                                                                   reply_markup=admin_markup); return ConversationHandler.END
    final_msg = f"✉️ **{sender}:**\n\n{msg_txt}"
    try:
        await context.bot.send_message(pid, final_msg, ParseMode.MARKDOWN);
        await query.edit_message_text(
            f"DM sent to player ID {pid}.")
    except Exception as e:
        logger.error(f"Failed DM to {pid}: {e}");
        await query.edit_message_text(f"Error sending DM: {e}")
    await query.message.reply_text("Admin Panel:", reply_markup=admin_markup)
    for k in ['dm_target_player_id', 'dm_sender_name', 'dm_message_text']: context.user_data.pop(k, None)
    return ConversationHandler.END


async def direct_message_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query;
    msg_obj = query.message if query else update.message
    if query:
        await query.answer();
        if query.message: await query.edit_message_text("DM cancelled.")
    else:
        await update.message.reply_text("DM cancelled.")

    await msg_obj.reply_text("Admin Panel:", reply_markup=get_admin_panel_keyboard())
    for k in ['dm_target_player_id', 'dm_sender_name', 'dm_message_text']: context.user_data.pop(k, None)
    return ConversationHandler.END


async def admin_list_players_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update.effective_user.id): await update.message.reply_text("No permission."); return
    if not player_data: await update.message.reply_text("Player list empty."); return
    msg_parts = ["**Player List:**\n"]
    sorted_players = sorted(player_data.items(), key=lambda item: item[1].get('character_name', ''))
    for pid, pInf in sorted_players:
        act_stat = "Active" if pInf.get("is_active") else "Inactive"
        game_stat = pInf.get("status", STATUS_UNDEFINED)
        sm_id = pInf.get("secret_mission_id")
        sm_title = secret_missions_data.get(sm_id, {}).get("title", "None") if sm_id else "None"
        msg_parts.append(
            f"- **{pInf.get('character_name', 'N/A')}** (ID: `{pid}`)\n  Act: {act_stat}, Status: {game_stat}\n  SM: {sm_title[:25]}"
        )
    full_msg = "\n".join(msg_parts)
    if len(full_msg) > 4096:
        # Split message into chunks if it's too long
        current_chunk = ""
        for part in msg_parts:
            if len(current_chunk) + len(part) > 4090:
                await update.message.reply_text(current_chunk, parse_mode=ParseMode.MARKDOWN)
                current_chunk = part
            else:
                current_chunk += "\n" + part
        if current_chunk:
            await update.message.reply_text(current_chunk, parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text(full_msg, parse_mode=ParseMode.MARKDOWN)


async def admin_update_mission_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update.effective_user.id): await update.message.reply_text("No permission."); return
    args = context.args;
    if len(args) < 2: await update.message.reply_text(
        "Usage: /admin_update_mission <player_ID|all> <mission_ID>"); return
    target, mission_id = args[0], args[1]
    if mission_id not in missions_data: await update.message.reply_text(
        f"Error: Mission '{mission_id}' not found."); return
    updated_p_ids = []
    if target.lower() == "all":
        for pid in player_data:
            player_data[pid]["current_mission_id"] = mission_id
            updated_p_ids.append(pid)
    else:
        try:
            pid = int(target)
            if pid in player_data:
                player_data[pid]["current_mission_id"] = mission_id
                updated_p_ids.append(pid)
            else:
                await update.message.reply_text(f"Player ID {pid} not found.");
                return
        except ValueError:
            await update.message.reply_text("Invalid Player ID.");
            return
    if updated_p_ids:
        if save_player_data():
            m_title = missions_data[mission_id].get('title', mission_id)
            player_names = [player_data[pid].get('character_name', pid) for pid in updated_p_ids]
            await update.message.reply_text(f"Mission '{m_title}' set for: {', '.join(map(str, player_names))}.")
            for p_id_notify in updated_p_ids:
                try:
                    await context.bot.send_message(p_id_notify, "❗ Your mission has been updated! Check /mission.")
                except Exception as e:
                    logger.warning(f"Failed to notify {p_id_notify} of mission update: {e}")
        else:
            await update.message.reply_text("Error saving player data.")
    elif target.lower() != "all":
        await update.message.reply_text("Failed to update mission for any player.")


async def admin_update_character_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update.effective_user.id): await update.message.reply_text("No permission."); return
    args = context.args
    if len(args) < 3:
        await update.message.reply_text("Usage: /admin_update_character <player_ID> <field> <value>")
        await update.message.reply_text(
            "Fields: character_name, role, bio, image_url, is_active, status, secret_mission_id")
        return
    try:
        pid = int(args[0])
    except ValueError:
        await update.message.reply_text("Player ID must be a number.");
        return
    field, value_str = args[1].lower(), " ".join(args[2:])

    if pid not in player_data:
        await update.message.reply_text(f"Player ID {pid} not found.");
        return

    valid_fields = ["character_name", "character_role", "character_bio", "character_image_url", "is_active", "status",
                    "secret_mission_id"]
    if field not in valid_fields: await update.message.reply_text(f"Invalid field. Valid: {valid_fields}"); return

    new_val = value_str
    if field == "is_active":
        new_val = value_str.lower() in ["true", "1", "yes", "on"]
    elif field == "status":
        if value_str not in VALID_PLAYER_STATUSES: await update.message.reply_text(
            f"Invalid status. Valid: {', '.join(VALID_PLAYER_STATUSES)}"); return
    elif field == "secret_mission_id":
        if value_str.lower() in ['none', 'clear', 'null', 'remove']:
            new_val = None
        elif value_str not in secret_missions_data:
            await update.message.reply_text(
                f"Error: Secret Mission ID '{value_str}' not found. Use 'clear' to remove.");
            return
    elif field == "image_url":
        # NEW: When the image_url is updated, clear the cached file_id to force a re-upload and re-cache
        player_data[pid]["character_image_file_id"] = None
        new_val = value_str

    player_data[pid][field] = new_val
    if save_player_data():
        p_name = player_data[pid].get('character_name', pid)
        await update.message.reply_text(f"Field '{field}' for {p_name} updated to: '{new_val}'.")
        try:
            await context.bot.send_message(pid,
                                           "❗ Your character info has been updated by a Game Master! Check `/character`.")
        except Exception as e:
            logger.warning(f"Failed to notify {pid} of char update: {e}")
    else:
        await update.message.reply_text("Error saving player data.")


async def admin_recipients_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global message_recipients
    if not is_admin(update.effective_user.id): await update.message.reply_text("No permission."); return
    args = context.args
    if not args: await update.message.reply_text("Usage: /admin_recipients [add|remove|list] [name]"); return
    action = args[0].lower()
    if action == "add":
        if len(args) < 2: await update.message.reply_text("Usage: add <name>"); return
        name = " ".join(args[1:])
        if name not in message_recipients:
            message_recipients.append(name)
            if save_recipients_data():
                await update.message.reply_text(f"Recipient '{name}' added.")
            else:
                if name in message_recipients: message_recipients.remove(name)
                await update.message.reply_text("Error saving.")
        else:
            await update.message.reply_text(f"Recipient '{name}' already exists.")
    elif action == "remove":
        if len(args) < 2: await update.message.reply_text("Usage: remove <name>"); return
        name = " ".join(args[1:])
        if name in message_recipients:
            orig = list(message_recipients)
            message_recipients.remove(name)
            if save_recipients_data():
                await update.message.reply_text(f"Recipient '{name}' removed.")
            else:
                message_recipients[:] = orig
                await update.message.reply_text("Error saving.")
        else:
            await update.message.reply_text(f"Recipient '{name}' not found.")
    elif action == "list":
        await update.message.reply_text(
            "**Message Recipients (NPCs):**\n" + "\n".join(
                f"- {r}" for r in message_recipients) if message_recipients else "List is empty.",
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        await update.message.reply_text("Invalid action. Use 'add', 'remove', or 'list'.")


# --- MAIN FUNCTION ---
def main() -> None:
    """Runs the bot."""
    load_data()

    application = Application.builder().token(BOT_TOKEN).build()

    # Player commands
    application.add_handler(MessageHandler(filters.Regex("^📚 Lore"), lore_command))
    application.add_handler(MessageHandler(filters.Regex("^👤 My character"), character_command))
    application.add_handler(MessageHandler(filters.Regex("^🎯 My mission"), mission_command))

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("lore", lore_command))
    application.add_handler(CommandHandler("character", character_command))
    application.add_handler(CommandHandler("mission", mission_command))

    application.add_handler(CallbackQueryHandler(lore_main_menu_trigger_callback, pattern="^lore_main_menu_trigger$"))
    application.add_handler(CallbackQueryHandler(lore_callback, pattern="^lore_"))

    # Send message conversation (player to DM)
    send_message_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("send_message", send_message_start),
                      MessageHandler(filters.Regex("^✉️ Send a message"), send_message_start)],
        states={CHOOSE_RECIPIENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_recipient)],
                TYPE_MESSAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, type_message)]},
        fallbacks=[CommandHandler("cancel", cancel_send_message),
                   MessageHandler(filters.Regex(r'(?i)^back$'), cancel_send_message)],
    )
    application.add_handler(send_message_conv_handler)

    # Admin Panel and its commands
    application.add_handler(CommandHandler("admin", admin_panel_command))
    application.add_handler(MessageHandler(filters.Regex("^⚙️ Admin Panel"), admin_panel_command))
    application.add_handler(MessageHandler(filters.Regex("^⬅️ Back to Main Menu"), back_to_main_menu_command))

    # Admin player activation/deactivation conversation
    admin_player_action_conv = ConversationHandler(
        entry_points=[CommandHandler("admin_activate_player", admin_activate_player_start),
                      MessageHandler(filters.Regex("^Activate Player$"), admin_activate_player_start),
                      CommandHandler("admin_deactivate_player", admin_deactivate_player_start),
                      MessageHandler(filters.Regex("^Deactivate Player$"), admin_deactivate_player_start)],
        states={SELECT_PLAYER_FOR_ACTION: [
            CallbackQueryHandler(process_player_action_selection, pattern="^(activate_|deactivate_)")]},
        fallbacks=[CallbackQueryHandler(cancel_admin_action, pattern="^.*_cancel$"),
                   CommandHandler("cancel", cancel_admin_action)],
        conversation_timeout=300
    )
    application.add_handler(admin_player_action_conv)

    # Admin Set Player Status Conversation
    admin_set_status_conv = ConversationHandler(
        entry_points=[CommandHandler("admin_set_player_status", admin_set_player_status_start),
                      MessageHandler(filters.Regex("^Set Player Status$"), admin_set_player_status_start)],
        states={
            SELECT_PLAYER_FOR_STATUS: [CallbackQueryHandler(set_player_status_select_player, pattern="^setstatus_")],
            SELECT_NEW_STATUS: [CallbackQueryHandler(set_player_status_select_new_status, pattern="^setstatus_")]},
        fallbacks=[CallbackQueryHandler(cancel_set_player_status, pattern="^setstatus_.*_cancel$"),
                   CommandHandler("cancel", cancel_set_player_status)],
        conversation_timeout=300
    )
    application.add_handler(admin_set_status_conv)

    # Admin Set Secret Mission Conversation
    admin_set_secret_mission_conv = ConversationHandler(
        entry_points=[
            CommandHandler("admin_set_secret_mission", admin_set_secret_mission_start),
            MessageHandler(filters.Regex("^Set Secret Mission$"), admin_set_secret_mission_start)
        ],
        states={
            SELECT_PLAYER_FOR_SECRET_MISSION: [
                CallbackQueryHandler(secret_mission_select_player, pattern="^secretmission_")],
            CHOOSE_SECRET_MISSION: [CallbackQueryHandler(secret_mission_choose_mission, pattern="^secretmission_set_")]
        },
        fallbacks=[
            CallbackQueryHandler(cancel_admin_action, pattern="^secretmission_cancel$"),
            CallbackQueryHandler(cancel_admin_action, pattern="^secretmission_set_.*_cancel_selection$"),
            CommandHandler("cancel", cancel_admin_action)
        ],
        conversation_timeout=300
    )
    application.add_handler(admin_set_secret_mission_conv)

    # Admin broadcast conversation
    admin_broadcast_conv = ConversationHandler(
        entry_points=[CommandHandler("admin_broadcast", admin_broadcast_start),
                      MessageHandler(filters.Regex("^Broadcast Message$"), admin_broadcast_start)],
        states={
            CHOOSE_BROADCAST_TARGET: [CallbackQueryHandler(broadcast_choose_target, pattern="^broadcast_target_")],
            TYPE_BROADCAST_SENDER_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, broadcast_type_sender)],
            TYPE_BROADCAST_MESSAGE_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, broadcast_type_message)],
            CONFIRM_BROADCAST_SEND: [CallbackQueryHandler(broadcast_confirm_send, pattern="^broadcast_confirm_")]
        },
        fallbacks=[CallbackQueryHandler(broadcast_cancel, pattern="^broadcast_cancel$"),
                   CommandHandler("cancel", broadcast_cancel)],
        conversation_timeout=300
    )
    application.add_handler(admin_broadcast_conv)

    # Admin direct message conversation
    admin_direct_message_conv = ConversationHandler(
        entry_points=[CommandHandler("admin_direct_message", admin_direct_message_start),
                      MessageHandler(filters.Regex("^Send Direct Message$"), admin_direct_message_start)],
        states={
            SELECT_DM_PLAYER: [CallbackQueryHandler(direct_message_select_player, pattern="^dmselect_")],
            TYPE_DM_SENDER_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, direct_message_type_sender_name)],
            TYPE_DM_MESSAGE_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, direct_message_type_text)],
            CONFIRM_DM_SEND: [CallbackQueryHandler(direct_message_confirm_send, pattern="^dm_confirm_")]
        },
        fallbacks=[CallbackQueryHandler(direct_message_cancel, pattern="^dmselect_cancel$"),
                   CommandHandler("cancel", direct_message_cancel)],
        conversation_timeout=300
    )
    application.add_handler(admin_direct_message_conv)

    # Other admin commands (as direct commands and text messages)
    application.add_handler(CommandHandler("admin_list_players", admin_list_players_command))
    application.add_handler(MessageHandler(filters.Regex("^List Players$"), admin_list_players_command))

    application.add_handler(CommandHandler("admin_update_mission", admin_update_mission_command))
    # Using only command for this to avoid accidental triggering.

    application.add_handler(CommandHandler("admin_update_character", admin_update_character_command))
    # Using only command for this to avoid accidental triggering.

    application.add_handler(CommandHandler("admin_recipients", admin_recipients_command))
    application.add_handler(MessageHandler(filters.Regex("^Manage Recipients$"), admin_recipients_command))

    logger.info("Bot is starting...")
    application.run_polling()


if __name__ == "__main__":
    main()
