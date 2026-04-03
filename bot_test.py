import os
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, ContextTypes, filters

# ---------------- SETTINGS ----------------

BOT_TOKEN = os.getenv("BOT_TOKEN")

# (Optional AI endpoint - you can keep or remove)
OLLAMA_URL = os.getenv("OLLAMA_URL")  # set in Railway if needed

# ---------------- COMMANDS ----------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🚀 Dravon is online. Send me anything.")

# ---------------- MESSAGE HANDLER ----------------

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text

    try:
        # If AI endpoint exists → use it
        if OLLAMA_URL:
            payload = {
                "model": "llama3",
                "prompt": user_text,
                "stream": False
            }

            res = requests.post(OLLAMA_URL, json=payload, timeout=30)
            res.raise_for_status()
            reply = res.json().get("response", "No response")

        else:
            # fallback (echo)
            reply = f"You said: {user_text}"

        await update.message.reply_text(reply)

    except Exception as e:
        await update.message.reply_text(f"⚠️ Error: {str(e)}")

# ---------------- MAIN ----------------

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("✅ Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()