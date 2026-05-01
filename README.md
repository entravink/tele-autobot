# Telegram Autobot

Control your PC remotely using a private Telegram bot.

## Features
- Change directories remotely
- Favorite folders
- List files
- Run Python scripts
- Delete files
- Take screenshots
- Download files
- Kill running scripts
- Authorized-user only access

## Requirements

- Python 3.9+
- Telegram account
- Bot token from BotFather

```bash
pip install python-telegram-bot python-dotenv pyautogui psutil mss asyncio
```

## Setup

Create `.env`:

```env
BOT_TOKEN=your_bot_token_here
AUTHORIZED_USER_ID=your_telegram_user_id
FAVORITES_JSON={"desktop":"C:/Users/YourName/Desktop","projects":"D:/Projects"}
```

## Run the Bot

### Manual
```bash
python service.py
```

### Startup Options

| OS | Method |
|---|---|
| Windows | Task Scheduler / Startup Folder |
| Linux | systemd |
| macOS | LaunchAgents |

## Commands

| Command | Usage | Description |
|---|---|---|
| `/cd` | `/cd projects` or directly input a custom directory `/cd D:\Downloads`| Change folder |
| `/list` | `/list` | List files |
| `/run` | `/run script.py` | Run Python script |
| `/delete` | `/delete file.txt` | Delete file |
| `/screenshot` | `/screenshot` | Take screenshot |
| `/download` | `/download report.xlsx` | Download file |
| `/kill` | `/kill script.py` | Kill running script |

## Security Notes

This bot can run commands and manage files on your PC. Keep your token private and only authorize your own Telegram ID.

## Troubleshooting

- Check bot token
- Check authorized user ID
- Ensure internet connection
- Keep the bot process running
- Screenshot requires desktop session