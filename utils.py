from config import DM_CHAT_ID, STATUS_UNDEFINED
from data_manager import get_player_data

def is_admin(user_id: int) -> bool:
    return user_id == DM_CHAT_ID

def get_player_status(user_id: int) -> str:
    player_data = get_player_data()
    player = player_data.get(user_id)
    if player:
        return player.get("status", STATUS_UNDEFINED)
    return STATUS_UNDEFINED

def is_player_active(user_id: int) -> bool:
    player_data = get_player_data()
    player = player_data.get(user_id)
    return player.get("is_active", False) if player else False