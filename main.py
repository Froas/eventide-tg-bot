import logging
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ConversationHandler

from config import BOT_TOKEN, DM_CHAT_ID
from data_manager import load_data
from player_handlers import *
from lore_handlers import *
from admin_handlers import *

# Logging setup
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Validation
if not BOT_TOKEN or BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN":
    logging.error("BOT_TOKEN not found or not set.")
if DM_CHAT_ID is None:
    logging.error("DM_CHAT_ID not found or not a valid integer.")
if not BOT_TOKEN or BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN" or DM_CHAT_ID is None:
    exit("Critical configuration missing. Please set BOT_TOKEN and DM_CHAT_ID.")


def main() -> None:
    """Runs the bot."""
    load_data()

    application = Application.builder().token(BOT_TOKEN).build()

    # Player commands
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("lore", lore_command))
    application.add_handler(CommandHandler("character", character_command))
    application.add_handler(CommandHandler("mission", mission_command))

    # Button handlers
    application.add_handler(MessageHandler(filters.Regex("^📚 Lore"), lore_command))
    application.add_handler(MessageHandler(filters.Regex("^👤 My character"), character_command))
    application.add_handler(MessageHandler(filters.Regex("^🎯 My mission"), mission_command))

    # Lore callbacks
    application.add_handler(CallbackQueryHandler(lore_main_menu_trigger_callback, pattern="^lore_main_menu_trigger$"))
    application.add_handler(CallbackQueryHandler(lore_callback, pattern="^lore_"))

    # Send message conversation
    send_message_conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("send_message", send_message_start),
            MessageHandler(filters.Regex("^✉️ Send a message"), send_message_start)
        ],
        states={
            CHOOSE_RECIPIENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_recipient)],
            TYPE_MESSAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, type_message)]
        },
        fallbacks=[
            CommandHandler("cancel", cancel_send_message),
            MessageHandler(filters.Regex(r'(?i)^back$'), cancel_send_message)
        ],
    )
    application.add_handler(send_message_conv_handler)

    # Admin commands
    application.add_handler(CommandHandler("admin", admin_panel_command))
    application.add_handler(MessageHandler(filters.Regex("^⚙️ Admin Panel"), admin_panel_command))
    application.add_handler(MessageHandler(filters.Regex("^⬅️ Back to Main Menu"), back_to_main_menu_command))

    # Admin player activation/deactivation
    admin_player_action_conv = ConversationHandler(
        entry_points=[
            CommandHandler("admin_activate_player", admin_activate_player_start),
            MessageHandler(filters.Regex("^Activate Player$"), admin_activate_player_start),
            CommandHandler("admin_deactivate_player", admin_deactivate_player_start),
            MessageHandler(filters.Regex("^Deactivate Player$"), admin_deactivate_player_start)
        ],
        states={
            SELECT_PLAYER_FOR_ACTION: [
                CallbackQueryHandler(process_player_action_selection, pattern="^(activate_|deactivate_)")
            ]
        },
        fallbacks=[
            CallbackQueryHandler(cancel_admin_action, pattern="^.*_cancel$"),
            CommandHandler("cancel", cancel_admin_action)
        ],
        conversation_timeout=300
    )
    application.add_handler(admin_player_action_conv)

    # Admin Set Player Status Conversation
    admin_set_status_conv = ConversationHandler(
        entry_points=[
            CommandHandler("admin_set_player_status", admin_set_player_status_start),
            MessageHandler(filters.Regex("^Set Player Status$"), admin_set_player_status_start)
        ],
        states={
            SELECT_PLAYER_FOR_STATUS: [CallbackQueryHandler(set_player_status_select_player, pattern="^setstatus_")],
            SELECT_NEW_STATUS: [CallbackQueryHandler(set_player_status_select_new_status, pattern="^setstatus_")]
        },
        fallbacks=[
            CallbackQueryHandler(cancel_set_player_status, pattern="^setstatus_.*_cancel$"),
            CommandHandler("cancel", cancel_set_player_status)
        ],
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
                CallbackQueryHandler(secret_mission_select_player, pattern="^secretmission_")
            ],
            CHOOSE_SECRET_MISSION: [
                CallbackQueryHandler(secret_mission_choose_mission, pattern="^secretmission_set_")
            ]
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
        entry_points=[
            CommandHandler("admin_broadcast", admin_broadcast_start),
            MessageHandler(filters.Regex("^Broadcast Message$"), admin_broadcast_start)
        ],
        states={
            CHOOSE_BROADCAST_TARGET: [CallbackQueryHandler(broadcast_choose_target, pattern="^broadcast_target_")],
            TYPE_BROADCAST_SENDER_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, broadcast_type_sender)],
            TYPE_BROADCAST_MESSAGE_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, broadcast_type_message)],
            CONFIRM_BROADCAST_SEND: [CallbackQueryHandler(broadcast_confirm_send, pattern="^broadcast_confirm_")]
        },
        fallbacks=[
            CallbackQueryHandler(broadcast_cancel, pattern="^broadcast_cancel$"),
            CommandHandler("cancel", broadcast_cancel)
        ],
        conversation_timeout=300
    )
    application.add_handler(admin_broadcast_conv)

    # Admin direct message conversation
    admin_direct_message_conv = ConversationHandler(
        entry_points=[
            CommandHandler("admin_direct_message", admin_direct_message_start),
            MessageHandler(filters.Regex("^Send Direct Message$"), admin_direct_message_start)
        ],
        states={
            SELECT_DM_PLAYER: [CallbackQueryHandler(direct_message_select_player, pattern="^dmselect_")],
            TYPE_DM_SENDER_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, direct_message_type_sender_name)],
            TYPE_DM_MESSAGE_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, direct_message_type_text)],
            CONFIRM_DM_SEND: [CallbackQueryHandler(direct_message_confirm_send, pattern="^dm_confirm_")]
        },
        fallbacks=[
            CallbackQueryHandler(direct_message_cancel, pattern="^dmselect_cancel$"),
            CommandHandler("cancel", direct_message_cancel)
        ],
        conversation_timeout=300
    )
    application.add_handler(admin_direct_message_conv)

    # Other admin commands
    application.add_handler(CommandHandler("admin_list_players", admin_list_players_command))
    application.add_handler(MessageHandler(filters.Regex("^List Players$"), admin_list_players_command))

    application.add_handler(CommandHandler("admin_update_mission", admin_update_mission_command))
    application.add_handler(MessageHandler(filters.Regex("^Update Mission$"), admin_update_mission_command))

    application.add_handler(CommandHandler("admin_update_character", admin_update_character_command))
    application.add_handler(MessageHandler(filters.Regex("^Update Character$"), admin_update_character_command))

    application.add_handler(CommandHandler("admin_recipients", admin_recipients_command))
    application.add_handler(MessageHandler(filters.Regex("^Manage Recipients$"), admin_recipients_command))

    logger.info("Bot is starting...")
    application.run_polling()


if __name__ == "__main__":
    main()