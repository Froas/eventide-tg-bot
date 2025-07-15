import logging
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from telegram.constants import ParseMode

from config import *
from data_manager import (get_player_data, get_secret_missions_data, save_player_data,
                          get_missions_data, save_missions_data, get_message_recipients,
                          save_recipients_data)
from utils import is_admin, get_player_status
from keyboards import *

logger = logging.getLogger(__name__)


async def admin_panel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("This command is for administrators only.")
        return
    await update.message.reply_text("Admin Panel:", reply_markup=get_admin_panel_keyboard())


async def back_to_main_menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Returning to main menu...",
                                    reply_markup=get_main_reply_keyboard(update.effective_user.id))


# Player activation/deactivation handlers
async def ask_player_for_action(update: Update, context: ContextTypes.DEFAULT_TYPE, action: str) -> int:
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("No permission.")
        return ConversationHandler.END

    context.user_data['admin_action'] = action
    keyboard = get_player_selection_keyboard(action_prefix=action, include_status_type="activation")

    if not keyboard:
        await update.message.reply_text("No players found.")
        return ConversationHandler.END

    action_text = "activate" if action == "activate" else "deactivate"
    await update.message.reply_text(f"Select player to {action_text}:", reply_markup=keyboard)
    return SELECT_PLAYER_FOR_ACTION


async def admin_activate_player_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    return await ask_player_for_action(update, context, "activate")


async def admin_deactivate_player_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    return await ask_player_for_action(update, context, "deactivate")


async def process_player_action_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    action_type_from_cb = query.data.split("_")[0]
    admin_markup = get_admin_panel_keyboard()

    if query.data.endswith("_cancel"):
        await query.edit_message_text("Action cancelled.")
        await query.message.reply_text("Admin Panel:", reply_markup=admin_markup)
        return ConversationHandler.END

    try:
        player_id = int(query.data.split("_")[-1])
    except (IndexError, ValueError):
        await query.edit_message_text("Invalid selection.")
        return SELECT_PLAYER_FOR_ACTION

    action = context.user_data.get('admin_action')
    if not action or action != action_type_from_cb:
        logger.error(f"Action mismatch: expected {action}, got {action_type_from_cb}")
        await query.edit_message_text("Action mismatch. Start over.")
        await query.message.reply_text("Admin Panel:", reply_markup=admin_markup)
        return ConversationHandler.END

    # ИСПРАВЛЕНО: Используем функцию-геттер
    player_data = get_player_data()

    if player_id in player_data:
        p_info = player_data[player_id]
        p_name = p_info.get('character_name', player_id)

        if action == "activate":
            if not p_info.get("is_active"):
                p_info["is_active"] = True
                msg = f"Player {p_name} activated."
            else:
                msg = f"Player {p_name} already active."
        elif action == "deactivate":
            if p_info.get("is_active"):
                p_info["is_active"] = False
                msg = f"Player {p_name} deactivated."
            else:
                msg = f"Player {p_name} already inactive."

        if save_player_data():
            await query.edit_message_text(msg)
            if action == "activate" and msg.endswith("activated."):
                try:
                    await context.bot.send_message(player_id,
                                                   "You have been activated for the mission. Godspeed!")
                except Exception as e:
                    logger.warning(f"Failed to notify player {player_id}: {e}")
            elif action == "deactivate" and msg.endswith("deactivated."):
                try:
                    await context.bot.send_message(player_id,
                                                   "Your account has been deactivated by the Game Master.")
                except Exception as e:
                    logger.warning(f"Failed to notify player {player_id}: {e}")
        else:
            await query.edit_message_text("Error saving data.")
    else:
        await query.edit_message_text(f"Player ID {player_id} not found.")

    await query.message.reply_text("Admin Panel:", reply_markup=admin_markup)
    return ConversationHandler.END


# Set player status handlers
async def admin_set_player_status_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("No permission.")
        return ConversationHandler.END

    keyboard = get_player_selection_keyboard(action_prefix="setstatus", include_status_type="game_status")
    if not keyboard:
        await update.message.reply_text("No players found.")
        return ConversationHandler.END

    await update.message.reply_text("Select player to set status:", reply_markup=keyboard)
    return SELECT_PLAYER_FOR_STATUS


async def set_player_status_select_player(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    if query.data.endswith("_cancel"):
        await query.edit_message_text("Set status cancelled.")
        await query.message.reply_text("Admin Panel:", reply_markup=get_admin_panel_keyboard())
        return ConversationHandler.END

    try:
        player_id = int(query.data.split("_")[-1])
    except (IndexError, ValueError):
        await query.edit_message_text("Invalid selection.")
        return SELECT_PLAYER_FOR_STATUS

    player_data = get_player_data()
    if player_id not in player_data:
        await query.edit_message_text("Player not found.")
        return SELECT_PLAYER_FOR_STATUS

    context.user_data['status_target_player_id'] = player_id
    p_name = player_data[player_id].get('character_name', player_id)
    current_status = player_data[player_id].get('status', STATUS_UNDEFINED)
    status_kb = get_status_selection_keyboard(player_id)

    await query.edit_message_text(f"Player: {p_name}. Current status: {current_status}.\nSelect new status:",
                                  reply_markup=status_kb)
    return SELECT_NEW_STATUS


async def set_player_status_select_new_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    admin_markup = get_admin_panel_keyboard()

    player_id = context.user_data.get('status_target_player_id')
    player_data = get_player_data()

    if not player_id or player_id not in player_data:
        await query.edit_message_text("Error: Player ID missing. Start over.")
        await query.message.reply_text("Admin Panel:", reply_markup=admin_markup)
        return ConversationHandler.END

    if query.data.endswith("_cancel"):
        await query.edit_message_text("Set status cancelled.")
        await query.message.reply_text("Admin Panel:", reply_markup=admin_markup)
        return ConversationHandler.END

    try:
        parts = query.data.split("_")
        new_status_encoded = "_".join(parts[2:])
        selected_status = None

        for s_val in VALID_PLAYER_STATUSES:
            encoded_valid_s = s_val.replace('(', '').replace(')', '').replace(' ', '_').lower()
            if encoded_valid_s == new_status_encoded:
                selected_status = s_val
                break

        if not selected_status:
            logger.error(f"Invalid status encoding '{new_status_encoded}' from callback '{query.data}'.")
            await query.edit_message_text("Invalid status selected. Please try again.")
            return SELECT_NEW_STATUS
    except (IndexError, ValueError) as e:
        logger.error(f"Error parsing status from cb: {query.data} - {e}")
        await query.edit_message_text("Error processing. Start over.")
        await query.message.reply_text("Admin Panel:", reply_markup=admin_markup)
        return ConversationHandler.END

    player_data[player_id]["status"] = selected_status
    if save_player_data():
        p_name = player_data[player_id].get('character_name', player_id)
        await query.edit_message_text(f"Status for {p_name} (ID: {player_id}) set to: {selected_status}.")
    else:
        await query.edit_message_text("Error saving status.")

    await query.message.reply_text("Admin Panel:", reply_markup=admin_markup)
    if 'status_target_player_id' in context.user_data:
        del context.user_data['status_target_player_id']
    return ConversationHandler.END


# Secret mission handlers
async def admin_set_secret_mission_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("No permission.")
        return ConversationHandler.END

    keyboard = get_player_selection_keyboard(action_prefix="secretmission", include_status_type="secret_mission")
    if not keyboard:
        await update.message.reply_text("No players found.")
        return ConversationHandler.END

    await update.message.reply_text("Select player for secret mission:", reply_markup=keyboard)
    return SELECT_PLAYER_FOR_SECRET_MISSION


async def secret_mission_select_player(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    if query.data.endswith("_cancel"):
        await query.edit_message_text("Set secret mission cancelled.")
        await query.message.reply_text("Admin Panel:", reply_markup=get_admin_panel_keyboard())
        return ConversationHandler.END

    try:
        player_id = int(query.data.split("_")[-1])
    except (IndexError, ValueError):
        await query.edit_message_text("Invalid selection.")
        return SELECT_PLAYER_FOR_SECRET_MISSION

    player_data = get_player_data()
    if player_id not in player_data:
        await query.edit_message_text("Player not found.")
        return SELECT_PLAYER_FOR_SECRET_MISSION

    context.user_data['secret_mission_player_id'] = player_id
    p_name = player_data[player_id].get('character_name', player_id)

    secret_mission_kb = get_secret_mission_selection_keyboard(player_id)
    current_sm_id = player_data[player_id].get("secret_mission_id")
    secret_missions_data = get_secret_missions_data()
    current_sm_title = secret_missions_data.get(current_sm_id, {}).get("title", "None") if current_sm_id else "None"

    await query.edit_message_text(
        f"Player: {p_name}. Current secret mission: {current_sm_title}.\nSelect new secret mission:",
        reply_markup=secret_mission_kb)
    return CHOOSE_SECRET_MISSION


async def secret_mission_choose_mission(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    admin_markup = get_admin_panel_keyboard()

    player_id = context.user_data.get('secret_mission_player_id')
    player_data = get_player_data()
    secret_missions_data = get_secret_missions_data()

    if not player_id or player_id not in player_data:
        await query.edit_message_text("Error: Player context lost. Start over.")
        await query.message.reply_text("Admin Panel:", reply_markup=admin_markup)
        return ConversationHandler.END

    if query.data.endswith("_cancel_selection"):
        await query.edit_message_text("Set secret mission cancelled.")
        await query.message.reply_text("Admin Panel:", reply_markup=admin_markup)
        return ConversationHandler.END

    if query.data == "secretmission_none":
        await query.edit_message_text("No secret missions defined. Action cancelled.")
        await query.message.reply_text("Admin Panel:", reply_markup=admin_markup)
        return ConversationHandler.END

    try:
        parts = query.data.split("_")
        action_player_id = int(parts[2])
        mission_id_to_set = "_".join(parts[3:]) if len(parts) > 3 else "clear"

        if len(parts) > 3 and parts[3] == "clear":
            mission_id_to_set = "clear"

        if action_player_id != player_id:
            await query.edit_message_text("Player ID mismatch. Start over.")
            await query.message.reply_text("Admin Panel:", reply_markup=admin_markup)
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
            if kb:
                await query.message.reply_text("Select new secret mission:", reply_markup=kb)
            return CHOOSE_SECRET_MISSION
    except Exception as e:
        logger.error(f"Error processing secret mission selection: {e}. Data: {query.data}")
        await query.edit_message_text("Error setting secret mission. Start over.")

    await query.message.reply_text("Admin Panel:", reply_markup=admin_markup)
    if 'secret_mission_player_id' in context.user_data:
        del context.user_data['secret_mission_player_id']
    return ConversationHandler.END


# Broadcast handlers
async def admin_broadcast_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("No permission.")
        return ConversationHandler.END

    await update.message.reply_text("Choose broadcast target:", reply_markup=get_broadcast_target_keyboard())
    return CHOOSE_BROADCAST_TARGET


async def broadcast_choose_target(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    target = query.data.split("_")[-1]

    if target == "cancel":
        await query.edit_message_text("Broadcast cancelled.")
        await query.message.reply_text("Admin Panel:", reply_markup=get_admin_panel_keyboard())
        return ConversationHandler.END

    context.user_data['broadcast_target'] = target
    await query.edit_message_text("Enter sender name (or 'default' for Game Master):")
    return TYPE_BROADCAST_SENDER_NAME


async def broadcast_type_sender(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    sender_name = update.message.text
    context.user_data['broadcast_sender'] = "Game Master" if sender_name.lower() == 'default' else sender_name
    await update.message.reply_text("Enter broadcast message text:")
    return TYPE_BROADCAST_MESSAGE_TEXT


async def broadcast_type_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['broadcast_message'] = update.message.text
    sender = context.user_data['broadcast_sender']
    target_map = {"all": "All", "active": "Active", "inactive": "Inactive"}
    target_disp = target_map.get(context.user_data['broadcast_target'], "Unknown")
    preview = f"--PREVIEW--\nFrom: {sender}\nTo: {target_disp} Players\n\n{context.user_data['broadcast_message']}\n\nConfirm send?"
    await update.message.reply_text(preview, reply_markup=get_confirmation_keyboard("broadcast_confirm_yes",
                                                                                    "broadcast_confirm_no"))
    return CONFIRM_BROADCAST_SEND


async def broadcast_confirm_send(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    admin_markup = get_admin_panel_keyboard()

    if query.data == "broadcast_confirm_no":
        await query.edit_message_text("Broadcast cancelled.")
        await query.message.reply_text("Admin Panel:", reply_markup=admin_markup)
        return ConversationHandler.END

    target = context.user_data.get('broadcast_target')
    sender = context.user_data.get('broadcast_sender')
    msg_txt = context.user_data.get('broadcast_message')

    if not all([target, sender, msg_txt]):
        await query.edit_message_text("Error: Broadcast data missing. Start over.")
        await query.message.reply_text("Admin Panel:", reply_markup=admin_markup)
        return ConversationHandler.END

    player_data = get_player_data()
    rec_ids = [pid for pid, p in player_data.items() if (
            target == "all" or (target == "active" and p.get("is_active")) or (
            target == "inactive" and not p.get("is_active")))]

    count = 0
    final_msg = f"📢 **{sender}:**\n\n{msg_txt}"

    for pid in rec_ids:
        try:
            await context.bot.send_message(pid, final_msg, parse_mode=ParseMode.MARKDOWN)
            count += 1
        except Exception as e:
            logger.error(f"Failed broadcast to {pid}: {e}")

    await query.edit_message_text(f"Broadcast sent to {count} players.")
    await query.message.reply_text("Admin Panel:", reply_markup=admin_markup)

    for k in ['broadcast_target', 'broadcast_sender', 'broadcast_message']:
        context.user_data.pop(k, None)
    return ConversationHandler.END


# Direct message handlers
async def admin_direct_message_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("No permission.")
        return ConversationHandler.END

    keyboard = get_player_selection_keyboard("dmselect", include_status_type=None)
    if not keyboard:
        await update.message.reply_text("No players found.")
        return ConversationHandler.END

    await update.message.reply_text("Select player for direct message:", reply_markup=keyboard)
    return SELECT_DM_PLAYER


async def direct_message_select_player(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    if query.data.endswith("_cancel"):
        await query.edit_message_text("DM cancelled.")
        await query.message.reply_text("Admin Panel:", reply_markup=get_admin_panel_keyboard())
        return ConversationHandler.END

    try:
        player_id = int(query.data.split("_")[-1])
    except (IndexError, ValueError):
        await query.edit_message_text("Invalid selection.")
        return SELECT_DM_PLAYER

    player_data = get_player_data()
    if player_id not in player_data:
        await query.edit_message_text("Player not found.")
        return SELECT_DM_PLAYER

    context.user_data['dm_target_player_id'] = player_id
    p_name = player_data[player_id].get('character_name', player_id)
    await query.edit_message_text(f"To: {p_name}.\nEnter sender name (or 'default' for Game Master):")
    return TYPE_DM_SENDER_NAME


async def direct_message_type_sender_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    sender_name = update.message.text
    context.user_data['dm_sender_name'] = "Game Master" if sender_name.lower() == 'default' else sender_name
    await update.message.reply_text("Enter message text:")
    return TYPE_DM_MESSAGE_TEXT


async def direct_message_type_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['dm_message_text'] = update.message.text
    pid = context.user_data['dm_target_player_id']
    player_data = get_player_data()
    p_name = player_data.get(pid, {}).get('character_name', pid)
    sender = context.user_data['dm_sender_name']
    preview = f"--PREVIEW DM--\nTo: {p_name}\nFrom: {sender}\n\n{context.user_data['dm_message_text']}\n\nConfirm?"
    await update.message.reply_text(preview, reply_markup=get_confirmation_keyboard("dm_confirm_yes", "dm_confirm_no"))
    return CONFIRM_DM_SEND


async def direct_message_confirm_send(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    admin_markup = get_admin_panel_keyboard()

    if query.data == "dm_confirm_no":
        await query.edit_message_text("DM cancelled.")
        await query.message.reply_text("Admin Panel:", reply_markup=admin_markup)
        return ConversationHandler.END

    pid = context.user_data.get('dm_target_player_id')
    sender = context.user_data.get('dm_sender_name')
    msg_txt = context.user_data.get('dm_message_text')

    if not all([pid, sender, msg_txt]):
        await query.edit_message_text("Error: DM data missing.")
        await query.message.reply_text("Admin Panel:", reply_markup=admin_markup)
        return ConversationHandler.END

    final_msg = f"✉️ **{sender}:**\n\n{msg_txt}"
    try:
        await context.bot.send_message(pid, final_msg, parse_mode=ParseMode.MARKDOWN)
        await query.edit_message_text(f"DM sent to player ID {pid}.")
    except Exception as e:
        logger.error(f"Failed DM to {pid}: {e}")
        await query.edit_message_text(f"Error sending DM: {e}")

    await query.message.reply_text("Admin Panel:", reply_markup=admin_markup)
    for k in ['dm_target_player_id', 'dm_sender_name', 'dm_message_text']:
        context.user_data.pop(k, None)
    return ConversationHandler.END


# List players command
async def admin_list_players_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("No permission.")
        return

    player_data = get_player_data()
    secret_missions_data = get_secret_missions_data()

    if not player_data:
        await update.message.reply_text("Player list empty.")
        return

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


# Update mission command
async def admin_update_mission_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("No permission.")
        return

    args = context.args
    if len(args) < 2:
        await update.message.reply_text("Usage: /admin_update_mission <player_ID|all> <mission_ID>")
        return

    target, mission_id = args[0], args[1]
    missions_data = get_missions_data()
    player_data = get_player_data()

    if mission_id not in missions_data:
        await update.message.reply_text(f"Error: Mission '{mission_id}' not found.")
        return

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
                await update.message.reply_text(f"Player ID {pid} not found.")
                return
        except ValueError:
            await update.message.reply_text("Invalid Player ID.")
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


# Update character command
async def admin_update_character_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("No permission.")
        return

    args = context.args
    if len(args) < 3:
        await update.message.reply_text("Usage: /admin_update_character <player_ID> <field> <value>")
        await update.message.reply_text(
            "Fields: character_name, character_role, character_bio, character_image_url, is_active, status, secret_mission_id")
        return

    try:
        pid = int(args[0])
    except ValueError:
        await update.message.reply_text("Player ID must be a number.")
        return

    field, value_str = args[1].lower(), " ".join(args[2:])
    player_data = get_player_data()
    secret_missions_data = get_secret_missions_data()

    if pid not in player_data:
        await update.message.reply_text(f"Player ID {pid} not found.")
        return

    valid_fields = ["character_name", "character_role", "character_bio", "character_image_url", "is_active", "status",
                    "secret_mission_id"]
    if field not in valid_fields:
        await update.message.reply_text(f"Invalid field. Valid: {valid_fields}")
        return

    new_val = value_str
    if field == "is_active":
        new_val = value_str.lower() in ["true", "1", "yes", "on"]
    elif field == "status":
        if value_str not in VALID_PLAYER_STATUSES:
            await update.message.reply_text(f"Invalid status. Valid: {', '.join(VALID_PLAYER_STATUSES)}")
            return
    elif field == "secret_mission_id":
        if value_str.lower() in ['none', 'clear', 'null', 'remove']:
            new_val = None
        elif value_str not in secret_missions_data:
            await update.message.reply_text(f"Error: Secret Mission ID '{value_str}' not found. Use 'clear' to remove.")
            return
    elif field == "character_image_url":
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


# Recipients management command
async def admin_recipients_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("No permission.")
        return

    args = context.args
    if not args:
        await update.message.reply_text("Usage: /admin_recipients [add|remove|list] [name]")
        return

    action = args[0].lower()
    message_recipients = get_message_recipients()

    if action == "add":
        if len(args) < 2:
            await update.message.reply_text("Usage: add <name>")
            return
        name = " ".join(args[1:])
        if name not in message_recipients:
            message_recipients.append(name)
            if save_recipients_data():
                await update.message.reply_text(f"Recipient '{name}' added.")
            else:
                if name in message_recipients:
                    message_recipients.remove(name)
                await update.message.reply_text("Error saving.")
        else:
            await update.message.reply_text(f"Recipient '{name}' already exists.")
    elif action == "remove":
        if len(args) < 2:
            await update.message.reply_text("Usage: remove <name>")
            return
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


# Cancel admin action
async def cancel_admin_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    msg_obj = query.message if query else update.message

    if query:
        await query.answer()
        await query.edit_message_text("Action cancelled.")
    else:
        await update.message.reply_text("Action cancelled.")

    await msg_obj.reply_text("Admin Panel:", reply_markup=get_admin_panel_keyboard())
    return ConversationHandler.END


# Cancel functions for different handlers
async def cancel_set_player_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    msg_obj = query.message if query else update.message

    if query:
        await query.answer()
        await query.edit_message_text("Set status cancelled.")
    else:
        await update.message.reply_text("Set status cancelled.")

    await msg_obj.reply_text("Admin Panel:", reply_markup=get_admin_panel_keyboard())
    if 'status_target_player_id' in context.user_data:
        del context.user_data['status_target_player_id']
    return ConversationHandler.END


async def broadcast_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    msg_obj = query.message if query else update.message

    if query:
        await query.answer()
        if query.message:
            await query.edit_message_text("Broadcast cancelled.")
    else:
        await update.message.reply_text("Broadcast cancelled.")

    await msg_obj.reply_text("Admin Panel:", reply_markup=get_admin_panel_keyboard())
    for k in ['broadcast_target', 'broadcast_sender', 'broadcast_message']:
        context.user_data.pop(k, None)
    return ConversationHandler.END


async def direct_message_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    msg_obj = query.message if query else update.message

    if query:
        await query.answer()
        if query.message:
            await query.edit_message_text("DM cancelled.")
    else:
        await update.message.reply_text("DM cancelled.")

    await msg_obj.reply_text("Admin Panel:", reply_markup=get_admin_panel_keyboard())
    for k in ['dm_target_player_id', 'dm_sender_name', 'dm_message_text']:
        context.user_data.pop(k, None)
    return ConversationHandler.END