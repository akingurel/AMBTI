# Discord RPG Bot

A comprehensive Discord bot with RPG elements, character management, and interactive features.

## Features

### 🎮 Character System
- Create and manage characters with stats (strength, money, level, XP, health, armor)
- Level up system with XP requirements
- Equipment system with inventory management

### ⚔️ Combat & Training
- `!train` - Train to gain strength and XP
- `!is_` - Work to earn money (with rare big rewards)
- `!savas [kolay/normal/zor]` - Battle system with different difficulty levels
- `!duello @user` - PvP duels between players

### 🛒 Economy & Items
- `!market` - Classic market with power packs, XP packs, and GIFs
- `!itemmarket` - Equipment market with weapons, armor, etc.
- `!envanter` - View your inventory and equipped items
- `!giy <item_code>` - Equip/unequip items

### 👹 Boss System
- Automatic boss spawns every 1-2 hours
- `!bossvurus` - Attack the boss
- `!bossdurum` - Check boss status
- Special rewards for defeating bosses

### 🔧 Admin Commands
- `!duyuru <message>` - Send announcements
- `!bossbelir` - Manually spawn a boss
- `!temizle <amount>` - Delete messages

## Setup

1. Install required dependencies:
```bash
pip install discord.py praw redgifs requests
```

2. Create a `config.json` file with your bot configuration:
```json
{
    "TOKEN": "your_discord_bot_token",
    "GIPHY_API_KEY": "your_giphy_api_key",
    "TENOR_API_KEY": "your_tenor_api_key",
    "ADMIN_IDS": [your_admin_user_ids],
    "OZEL_KULLANICILAR": [special_user_ids],
    "BOSS_NSFWMARKET_USERS": [],
    "KAWAII_TOKEN": "your_kawaii_token"
}
```

3. Create the required data files:
- `karakterler.json` - Character data storage
- `itemler.json` - Item definitions
- `dm_log.json` - DM message logging

4. Run the bot:
```bash
python main.py
```

## File Structure

- `main.py` - Main bot code
- `config.json` - Bot configuration (not included in repo for security)
- `karakterler.json` - Character data storage
- `itemler.json` - Item definitions and market data
- `dm_log.json` - DM message logging
- `test_kawaii.py` - Testing file for Kawaii API

## Commands

### Basic Commands
- `!karakter [@user]` - View character stats
- `!yardim` - Show help and command list

### Character Management
- `!train` - Train to increase strength
- `!is_` - Work to earn money
- `!envanter` - View inventory and equipment
- `!giy <item_code>` - Equip/unequip items

### Combat
- `!savas [kolay/normal/zor]` - Battle with different difficulties
- `!duello @user` - Challenge another player to a duel

### Economy
- `!market` - View classic market
- `!itemmarket` - View equipment market
- `!satinal <code>` - Purchase items

### Boss System
- `!bossvurus` - Attack the current boss
- `!bossdurum` - Check boss status

### Admin Only
- `!duyuru <message>` - Send server announcement
- `!bossbelir` - Spawn a boss manually
- `!temizle <amount>` - Delete messages

## Requirements

- Python 3.7+
- discord.py
- praw
- redgifs
- requests

## License

This project is for educational purposes. Please ensure you have proper permissions to use any APIs or services integrated in this bot.
