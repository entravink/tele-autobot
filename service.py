import os
import subprocess
import signal
import pyautogui
import psutil
import json
from dotenv import load_dotenv
from telegram import Update, BotCommand
from telegram.ext import Application, CommandHandler, ContextTypes
import mss
import asyncio

# --- 1. CONFIGURATION ---
load_dotenv()  # Load from .env file
BOT_TOKEN = os.getenv("BOT_TOKEN")
AUTHORIZED_USER_ID = int(os.getenv("AUTHORIZED_USER_ID", 0))

# Load Favorites from JSON string in .env
fav_json_string = os.getenv("FAVORITES_JSON", "{}")
try:
    FAVORITES = json.loads(fav_json_string)
except json.JSONDecodeError:
    print("❌ Error: FAVORITES_JSON in .env is not valid JSON.")
    FAVORITES = {"default": os.getcwd()}

# Set CURRENT_PATH to the first item in FAVORITES dynamically
if FAVORITES:
    # list(FAVORITES.values())[0] grabs the first path in the dictionary
    CURRENT_PATH = list(FAVORITES.values())[0]
else:
    CURRENT_PATH = os.getcwd()

#print(f"🤖 Bot started. Default folder: {CURRENT_PATH}")

# --- 2. SECURITY MIDDLEWARE ---
def is_authorized(update: Update):
    return update.effective_user.id == AUTHORIZED_USER_ID

# --- 3. COMMAND HANDLERS ---

async def change_directory(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global CURRENT_PATH
    if not is_authorized(update): return
    
    if not context.args:
        fav_text = "\n".join([f"⭐ {k}: `{v}`" for k, v in FAVORITES.items()])
        await update.message.reply_text(f"📍 *Current:* `{CURRENT_PATH}`\n\n📌 *Favorites:*\n{fav_text}", parse_mode="Markdown")
        return

    target = context.args[0].lower()
    if target in FAVORITES:
        CURRENT_PATH = FAVORITES[target]
        await update.message.reply_text(f"🚀 Jumped to **{target}**")
    else:
        new_path = " ".join(context.args)
        if os.path.exists(new_path):
            CURRENT_PATH = new_path
            await update.message.reply_text(f"📂 Switched to custom path:\n`{CURRENT_PATH}`", parse_mode="Markdown")
        else:
            await update.message.reply_text("❌ Path not found.")

async def list_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update): return
    try:
        files = os.listdir(CURRENT_PATH)
        msg = "\n".join([f"📄 {f}" for f in files]) if files else "Folder is empty."
        await update.message.reply_text(f"📍 `{CURRENT_PATH}`\n\n{msg}", parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

async def run_script(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update): return
    if not context.args:
        await update.message.reply_text("Usage: /run [-3.xx] <script.py> [args]")
        return
    
    # Use 'py' launcher instead of 'python'
    cmd = ['py'] + context.args
    cmd_text = " ".join(cmd)
    
    try:
        subprocess.Popen(cmd, cwd=CURRENT_PATH)
        await update.message.reply_text(f"🚀 Executing `{cmd_text}` in `{CURRENT_PATH}`", parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ Execution failed: {e}")

async def run_output(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update): return
    if not context.args:
        await update.message.reply_text("Usage: /runout [-3.xx] <script.py> [args]")
        return
    
    # Use 'py' launcher instead of 'python'
    cmd = ['py'] + context.args
    cmd_text = " ".join(cmd)
    
    status_msg = await update.message.reply_text(f"⏳ Running `{cmd_text}`...")
    
    try:
        result = await asyncio.wait_for(
            asyncio.to_thread(
                subprocess.run, 
                cmd, 
                cwd=CURRENT_PATH, 
                capture_output=True, 
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            ),
            timeout=30
        )
        
        output = result.stdout.strip()
        errors = result.stderr.strip()
        
        response = ""
        if output: response += f"✅ **Output:**\n```\n{output[:3500]}\n```"
        if errors: response += f"\n\n⚠️ **Errors:**\n```\n{errors[:500]}\n```"
        if not output and not errors: response = "✅ Script finished (no output)."

        await status_msg.edit_text(response, parse_mode="Markdown")
        
    except TimeoutError:
        await status_msg.edit_text(
            f"🕒 `{cmd_text}` is taking a long time (> 30s).\n"
            "It is still running in the background, but I've stopped waiting for the output."
        )
    except Exception as e:
        await status_msg.edit_text(f"❌ Execution failed: {e}")
                		
async def delete_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update): return
    if not context.args: return await update.message.reply_text("Usage: /delete <filename>")
    
    target = os.path.join(CURRENT_PATH, context.args[0])
    try:
        if os.path.exists(target):
            os.remove(target)
            await update.message.reply_text(f"🗑️ Deleted `{context.args[0]}`")
        else:
            await update.message.reply_text("❌ File not found.")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

async def take_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update): return
    path = "temp_ss.png"
    try:
        with mss.mss() as sct:
            # Captures the primary monitor
            sct.shot(output=path)
        
        with open(path, 'rb') as photo:
            await update.message.reply_photo(photo=photo, caption="📸 Screenshot")
        os.remove(path)
    except Exception as e:
        await update.message.reply_text(f"❌ Screenshot failed: {e}")

async def download_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update): return
    if not context.args: return await update.message.reply_text("Usage: /download <filename>")
    
    path = os.path.join(CURRENT_PATH, context.args[0])
    if os.path.exists(path):
        await update.message.reply_document(document=open(path, 'rb'))
    else:
        await update.message.reply_text("❌ File not found.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update): return
    
    help_text = (
        "🤖 *Bot Command Menu*\n\n"
        "📂 *Navigation & Files*\n"
        "• `/cd` — Show current directory & favorites\n"
        "• `/cd <path/alias>` — Change directory or jump to favorite\n"
        "• `/list` — List files in current directory\n"
        "• `/download <filename>` — Download a file\n"
        "• `/delete <filename>` — Delete a file\n\n"
        "🚀 *Script Execution*\n"
        "• `/run [-3.xx] <script.py>` — Run script in background\n"
        "• `/runout [-3.xx] <script.py>` — Run script and show output/errors\n"
        "• `/kill <script.py>` — Terminate running script\n\n"
        "📸 *System*\n"
        "• `/screenshot` — Take a screenshot of main display\n"
        "• `/help` — Show this menu"
    )
    await update.message.reply_text(help_text, parse_mode="Markdown")

async def post_init(application: Application):
    # This automatically registers the commands into Telegram's menu button
    commands = [
        BotCommand("help", "Show list of available commands"),
        BotCommand("cd", "Change directory or show current path"),
        BotCommand("list", "List files in current folder"),
        BotCommand("run", "Run a script in background"),
        BotCommand("runout", "Run a script and capture output"),
        BotCommand("kill", "Kill a running script process"),
        BotCommand("download", "Download file from server"),
        BotCommand("delete", "Delete file from server"),
        BotCommand("screenshot", "Take screenshot of screen"),
    ]
    await application.bot.set_my_commands(commands)

async def kill_script(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update): return
    if not context.args: return await update.message.reply_text("Usage: /kill <name.py>")
    
    target = context.args[0]
    for proc in psutil.process_iter(['pid', 'cmdline']):
        if target in (proc.info['cmdline'] or []):
            os.kill(proc.info['pid'], signal.SIGTERM)
            await update.message.reply_text(f"🛑 Terminated {target}")
            return
    await update.message.reply_text(f"❌ {target} is not running.")

# --- 4. MAIN ENTRY POINT ---
if __name__ == "__main__":
    app = Application.builder().token(BOT_TOKEN).post_init(post_init).build()
    
    app.add_handler(CommandHandler("start", help_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("cd", change_directory))
    app.add_handler(CommandHandler("list", list_files))
    app.add_handler(CommandHandler("run", run_script))
    app.add_handler(CommandHandler("delete", delete_file))
    app.add_handler(CommandHandler("screenshot", take_screenshot))
    app.add_handler(CommandHandler("download", download_file))
    app.add_handler(CommandHandler("kill", kill_script))
    app.add_handler(CommandHandler("runout", run_output))
    
    print("Bot is listening for commands...")
    app.run_polling()