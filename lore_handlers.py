import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from data_manager import get_lore_data, save_lore_data
from config import BASE_DIR
from data_manager import lore_data, save_lore_data
from utils import is_admin, is_player_active
from keyboards import get_lore_main_menu_keyboard

logger = logging.getLogger(__name__)


async def lore_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user_id = query.from_user.id

    if not is_admin(user_id) and not is_player_active(user_id):
        await query.answer("Your account is awaiting activation by the Game Master.", show_alert=True)
        return

    await query.answer()
    lore_data = get_lore_data()

    callback_path_str = query.data[len("lore_"):]
    path_keys = callback_path_str.split("_sections_")

    current_level = lore_data
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
                    navigated_successfully = False
                    break
        else:
            if i == 0 and isinstance(lore_data.get(key), str):
                current_level = lore_data[key]
                path_objects.append(current_level)
            else:
                logger.warning(f"Key '{key}' not found in path. Full Callback: '{query.data}'.")
                navigated_successfully = False
            break

    if not navigated_successfully:
        if query.message:
            await query.edit_message_text(text="Error navigating lore data. Please try /lore again.")
        return

    text_content = "Information not found."
    keyboard_buttons = []
    image_container = None

    if len(path_keys) == 1:
        parent_callback_data = "lore_main_menu_trigger"
    else:
        parent_callback_data = "lore_" + "_sections_".join(path_keys[:-1])

    keyboard_buttons.append([InlineKeyboardButton("⬅️ Back", callback_data=parent_callback_data)])

    if isinstance(current_level, str):
        text_content = current_level
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

    if not query.message:
        return

    try:
        has_photo_info = image_container and ("image_url" in image_container or "image_file_id" in image_container)
        await query.message.delete()
        sent_message = None

        if has_photo_info:
            file_id = image_container.get("image_file_id")
            image_url = image_container.get("image_url")

            photo_to_send = file_id
            if not photo_to_send:
                if image_url.startswith("./") or not image_url.startswith("http"):
                    image_path = os.path.join(BASE_DIR, image_url.lstrip("./"))
                    if os.path.exists(image_path):
                        photo_to_send = open(image_path, 'rb')
                else:
                    photo_to_send = image_url

            if photo_to_send:
                try:
                    sent_message = await context.bot.send_photo(
                        chat_id=query.message.chat_id,
                        photo=photo_to_send
                    )
                    if not file_id and sent_message and sent_message.photo:
                        image_container["image_file_id"] = sent_message.photo[-1].file_id
                        logger.info(f"Cached lore image file_id for path: {callback_path_str}")
                        save_lore_data()
                except Exception as e_photo:
                    logger.error(f"Failed to send lore photo {image_url}: {e_photo}")

        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=text_content,
            reply_markup=keyboard_markup,
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        logger.error(f"Error in lore_callback: {e}. Path: {query.data}")
        try:
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
            await query.message.reply_text('Select a section to study:', reply_markup=reply_markup)
    elif query.message:
        await query.edit_message_text("Lore sections not found.")