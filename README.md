# Eventide: Eclipse | Comlog - Telegram RPG Bot 

A sophisticated Telegram bot designed for running tabletop RPG sessions, specifically built for the "Eventide: Eclipse" campaign. This bot serves as a digital game master assistant, managing player data, lore, missions, and in-character communications.

---

🎯 **Features**

* Player Management: Registration, activation/deactivation, status tracking
* Interactive Lore System: Hierarchical lore browser with image support and file caching
* Mission System: Regular and secret mission assignments
* In-Character Messaging: Player-to-player and player-to-NPC communication with status-based filtering
* Admin Panel: Comprehensive game master tools for campaign management
* Status Effects: Player status system (Active, Arrested, Hacked, Dead, etc.) affecting gameplay
* Broadcast System: Mass messaging to all or filtered player groups
* Data Persistence: JSON-based data storage with automatic saving

---

🏗️ **Project Structure**

```
eventide-bot/
├── main.py                 # Main application entry point and handler registration
├── config.py              # Configuration, constants, and environment variables
├── data_manager.py        # Data loading, saving, and management functions
├── utils.py               # Utility functions (permissions, player status checks)
├── keyboards.py           # Telegram keyboard layouts and UI components
├── player_handlers.py     # Player command handlers (start, lore, character, mission, messaging)
├── lore_handlers.py       # Lore system callbacks and navigation
├── admin_handlers.py      # Administrative command handlers and conversations
├── .env                   # Environment variables (not in repo)
├── requirements.txt       # Python dependencies
└── data/                  # JSON data files
    ├── lore_data.json
    ├── player_data.json
    ├── missions_data.json
    ├── recipients_data.json
    └── secret_missions_data.json
```

---

🛠️ **Technologies Used**

* Python 3.8+
* python-telegram-bot: Telegram Bot API wrapper
* python-dotenv: Environment variable management
* JSON: Data storage format
* Logging: Built-in Python logging for debugging and monitoring

---

📋 **Requirements**

```
python-telegram-bot>=20.0
python-dotenv>=0.19.0
```

---

⚙️ **Setup and Installation**

1. Clone the repository:

   ```sh
   git clone https://github.com/Froas/eventide-tg-bot
   cd eventide-tg-bot
   ```

2. Install dependencies:

   ```sh
   pip install -r requirements.txt
   ```

3. Create environment file:

   ```sh
   cp .env.example .env
   ```

4. Configure environment variables in .env:

   ```
   BOT_TOKEN=your_telegram_bot_token
   DM_CHAT_ID=your_admin_telegram_id
   LORE_FILE_PATH=data/lore_data.json
   PLAYERS_FILE_PATH=data/player_data.json
   MISSIONS_FILE_PATH=data/missions_data.json
   RECIPIENTS_FILE_PATH=data/recipients_data.json
   SECRET_MISSIONS_FILE_PATH=data/secret_missions_data.json
   ```

5. Create data directory and files:

   ```sh
   mkdir data
   # Create initial JSON files (see Data Structure section)
   ```

6. Run the bot:

   ```sh
   python main.py
   ```

---

📊 **Data Structure**

**Player Data (player\_data.json)**

```json
[
  {
    "telegram_user_id": 123456789,
    "character_name": "Agent Smith",
    "character_role": "Infiltrator",
    "character_bio": "A skilled operative...",
    "character_image_url": "./assets/characters/smith.jpg",
    "character_image_file_id": "cached_telegram_file_id",
    "is_active": true,
    "status": "Active (on mission)",
    "secret_mission_id": "mission_001",
    "current_mission_id": "main_mission_01",
    "ver": "1.0.0"
  }
]
```

**Lore Data (lore\_data.json)**

```json
{
  "introduction": "Welcome to Eventide: Eclipse...",
  "factions": {
    "title": "Factions",
    "description": "The major powers...",
    "image_url": "./assets/lore/factions.jpg",
    "sections": {
      "earth_federation": {
        "title": "Earth Federation",
        "description": "The governing body...",
        "image_url": "./assets/lore/earth_fed.jpg"
      }
    }
  }
}
```

**Missions Data (missions\_data.json)**

```json
{
  "main_mission_01": {
    "title": "Operation Nightfall",
    "description": "Infiltrate the enemy base...",
    "objectives": [
      "Gather intelligence",
      "Avoid detection",
      "Report back"
    ]
  }
}
```

---

🎮 **Core Components**

**1. Main Application (main.py)**

* Bot initialization and configuration
* Handler registration for commands and conversations
* Application lifecycle management

**2. Data Manager (data\_manager.py)**

* JSON file loading and saving
* Data validation and error handling
* Getter functions for safe data access

**3. Player Handlers (player\_handlers.py)**

* /start - Player registration
* /character - Character information display
* /mission - Current mission details
* /lore - Interactive lore browser
* Message sending system with status filtering

**4. Admin Handlers (admin\_handlers.py)**

* Player activation/deactivation
* Status management
* Mission assignment
* Broadcast messaging
* Direct messaging
* Character updates

**5. Lore System (lore\_handlers.py)**

* Hierarchical navigation
* Image caching for performance
* Dynamic keyboard generation

**6. UI Components (keyboards.py)**

* Inline and reply keyboard layouts
* Dynamic button generation
* User interface consistency

---

🔧 **Key Features Explained**

**Status System**

Players can have different statuses that affect their gameplay:

* Active (on mission): Normal gameplay
* Arrested: Communications monitored by ELLI
* Hacked: Messages intercepted by Technocrats
* Dead: No communication possible
* Traitor: Special status for plot purposes

**Message Filtering**

The bot implements sophisticated message filtering based on player status:

* Arrested players trigger security alerts
* Hacked players have messages intercepted
* Dead players receive no responses

**Image Caching**

To improve performance, the bot caches Telegram file IDs for images:

* First upload stores the file ID
* Subsequent uses reference the cached ID
* Reduces upload time and bandwidth

---

🚀 **Future Improvements**

**High Priority**

* Database Integration: Replace JSON with PostgreSQL/SQLite
* Dice Rolling System: Integrated dice mechanics
* Combat System: Turn-based combat management
* Inventory Management: Item tracking and trading
* Session Logging: Complete game session records

**Medium Priority**

* Web Dashboard: Browser-based admin interface
* Player Statistics: Detailed analytics and reports
* Backup System: Automated data backups
* Multi-Campaign Support: Support for multiple concurrent games
* Voice Message Support: Audio communication features

**Low Priority**

* Mobile App: Dedicated mobile application
* AI Integration: ChatGPT integration for NPC responses
* Map System: Interactive campaign maps
* Calendar Integration: Session scheduling
* Plugin System: Modular feature extensions

---

🐛 **Known Issues**

* Callback data length limitations (64 characters max)
* Large message splitting could be improved
* Image upload error handling needs enhancement
* Conversation timeout handling could be more graceful

---

🤝 **Contributing**

1. Fork the repository
2. Create a feature branch (git checkout -b feature/amazing-feature)
3. Commit your changes (git commit -m 'Add amazing feature')
4. Push to the branch (git push origin feature/amazing-feature)
5. Open a Pull Request

**Development Guidelines**

* Follow PEP 8 style guidelines
* Add docstrings to all functions
* Include error handling for external API calls
* Write unit tests for new features
* Update documentation for any changes

---

📝 **License**

This project is licensed under the MIT License - see the LICENSE file for details.

---

🔗 **Links**

* Repository: [Eventide Bot](https://github.com/Froas/eventide-tg-bot)
* Telegram Bot API: [API](https://core.telegram.org/bots/api)

---

📞 **Support**

For support, please open an issue on GitHub or contact the maintainer directly.

---

🙏 **Acknowledgments**

* Built for the "Eventide: Eclipse" tabletop RPG campaign
* Inspired by modern digital tabletop tools
* Thanks to the python-telegram-bot community for excellent documentation

---
## 📄 License

[MIT](https://github.com/Froas/eventide-tg-bot/blob/master/LICENSE)

---

**Made with ❤️ by [Froas](https://github.com/Froas)**

---