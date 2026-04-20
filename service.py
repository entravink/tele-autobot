import os
import subprocess
import signal
import pyautogui
import psutil
import json
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import mss

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
        await update.message.reply_text("Usage: /run <script.py> [args]")
        return
    
    cmd = ['python', context.args[0]] + context.args[1:]
    try:
        subprocess.Popen(cmd, cwd=CURRENT_PATH)
        await update.message.reply_text(f"🚀 Executing `{context.args[0]}` in `{CURRENT_PATH}`", parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ Execution failed: {e}")

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
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("cd", change_directory))
    app.add_handler(CommandHandler("list", list_files))
    app.add_handler(CommandHandler("run", run_script))
    app.add_handler(CommandHandler("delete", delete_file))
    app.add_handler(CommandHandler("screenshot", take_screenshot))
    app.add_handler(CommandHandler("download", download_file))
    app.add_handler(CommandHandler("kill", kill_script))
    
    print("Bot is listening for commands...")
    app.run_polling()