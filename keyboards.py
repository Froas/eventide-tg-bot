from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
import logging
from utils import is_admin
from data_manager import get_lore_data, get_player_data, get_secret_missions_data, get_message_recipients
from config import VALID_PLAYER_STATUSES

logger = logging.getLogger(__name__)


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
    lore_data = get_lore_data()
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
    player_data = get_player_data()
    secret_missions_data = get_secret_missions_data()

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
            current_player_status = p_info.get('status', 'Undefined')
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
    secret_missions_data = get_secret_missions_data()

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
    message_recipients = get_message_recipients()
    player_data = get_player_data()

    all_recipients = list(message_recipients)
    player_names = [p_info.get("character_name", f"Player {pid}") for pid, p_info in player_data.items() if
                    pid != sender_id and p_info.get("is_active")]
    all_recipients.extend(player_names)
    if not all_recipients:
        return None
    all_recipients.sort()
    keyboard = [[name] for name in all_recipients]
    keyboard.append(["Back"])
    return ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)