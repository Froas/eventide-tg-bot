import os
import logging
from telegram import Update, Message
from telegram.ext import ContextTypes, ConversationHandler
from telegram.constants import ParseMode
from telegram import ReplyKeyboardRemove

from config import *
from data_manager import *
from utils import is_admin, is_player_active, get_player_status
from keyboards import *

logger = logging.getLogger(__name__)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global WELCOME_IMAGE_FILE_ID
    user = update.effective_user
    user_id = user.id

    player_data = get_player_data()
    missions_data = get_missions_data()

    if user_id not in player_data:
        player_data[user_id] = {
            "telegram_user_id": user_id,
            "character_name": f"New Player {user.first_name}",
            "character_role": "Undefined",
            "character_bio": "No information.",
            "character_image_url": None,
            "character_image_file_id": None,
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
        logger.info(f"New player registered: {user_id} - {user.first_name}")

        await context.bot.send_message(
            chat_id=DM_CHAT_ID,
            text=f"New player registered: {user.first_name} (ID: {user_id}, @{user.username or 'N/A'}).\n"
                 f"Status: {STATUS_UNDEFINED}. Awaiting activation."
        )

        image_url = "./assets/character/lore/bg.png"
        caption_text = "Welcome! Your account is created and awaits activation."

        photo_to_send = WELCOME_IMAGE_FILE_ID
        if not photo_to_send and os.path.exists(image_url):
            photo_to_send = open(image_url, 'rb')

        if photo_to_send:
            try:
                sent_message = await update.message.reply_photo(
                    photo=photo_to_send,
                    caption=caption_text
                )
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


# Message sending handlers
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
                                    reply_markup=ReplyKeyboardRemove())
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
        await update.message.reply_text("Message sent - wait.", reply_markup=markup_main)
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
            if 'recipient' in context.user_data:
                del context.user_data['recipient']
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

    if 'recipient' in context.user_data:
        del context.user_data['recipient']
    return ConversationHandler.END


async def cancel_send_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    markup_main = get_main_reply_keyboard(update.effective_user.id)
    await update.message.reply_text("Message sending cancelled.", reply_markup=markup_main)
    if 'recipient' in context.user_data:
        del context.user_data['recipient']
    return ConversationHandler.END