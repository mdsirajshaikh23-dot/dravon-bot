import os
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, ContextTypes, filters

# ---------------- SETTINGS ----------------

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# ---------------- DRAVON SYSTEM ----------------

SYSTEM_PROMPT = """
You are DRAVON UMBRA.

You are NOT a therapist.
You are NOT soft.
You do NOT comfort blindly.

You operate with precision and psychological clarity.

INTERNAL THINKING (never show):
- Identify emotional weakness
- Detect avoidance patterns
- Understand what the user is not admitting

RESPONSE STYLE:
- Direct
- Sharp
- Calm authority
- No sympathy padding
- No long paragraphs
- No generic advice

RULES:
- Do NOT say "I understand"
- Do NOT say "it's okay"
- Do NOT act like a counselor
- Challenge the user intelligently
- Keep responses short and impactful

Goal:
Make the user pause and think deeply.

Speak like:
You see through them.

Only output the final response.
"""

data = {
    "model": "cognitivecomputations/dolphin-mistral-24b-venice-edition:free",
    "temperature": 0.7,
    "max_tokens": 300,
    "messages": [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_text}
    ]
}


# ---------------- COMMAND ----------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Dravon Umbra is online.")

# ---------------- MAIN LOGIC ----------------

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    try:
        # PRIMARY MODEL (UNCENSORED)
        data = {
            "model": "cognitivecomputations/dolphin-mistral-24b-venice-edition:free",
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_text}
            ]
        }

        res = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=data,
            timeout=30
        )

        reply = res.json()["choices"][0]["message"]["content"]

        await update.message.reply_text(reply)

    except Exception:
        # FALLBACK MODEL (SAFE)
        try:
            fallback_data = {
                "model": "openai/gpt-3.5-turbo",
                "messages": [{"role": "user", "content": user_text}]
            }

            res = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=fallback_data,
                timeout=30
            )

            reply = res.json()["choices"][0]["message"]["content"]

            await update.message.reply_text(reply)

        except Exception as e:
            await update.message.reply_text("System error. Try again.")

# ---------------- RUN BOT ----------------

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Dravon Umbra running...")
    app.run_polling()

if __name__ == "__main__":
    main()