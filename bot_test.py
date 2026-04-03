import requests
import json
import datetime
import os
import asyncio

from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes

# ---------------- SETTINGS ----------------

BOT_TOKEN = os.getenv("BOT_TOKEN")

OLLAMA_URL = "https://enforcedly-unsymptomatic-jacqulyn.ngrok-free.dev/api/generate"

LIMIT = 5
usage = {}

MEMORY_FILE = "memory.json"

PAYMENT_LINK = "https://rzp.io/rzp/llzYADe"

HEADERS = {"Content-Type": "application/json"}

# ---------------- MEMORY ----------------

def load_memory():
    try:
        with open(MEMORY_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_memory(memory):
    with open(MEMORY_FILE, "w") as f:
        json.dump(memory, f, indent=2)

# ---------------- PAYMENT ----------------

async def upgrade(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = f"""
🚀 Upgrade to Dravon Umbra Pro

Unlimited strategic advice for corporate dominance.

Price: ₹499

Pay here:
{PAYMENT_LINK}
"""
    await update.message.reply_text(message)

# ---------------- MAIN REPLY ----------------

async def reply(update: Update, context: ContextTypes.DEFAULT_TYPE):

    memory = load_memory()

    user_id = str(update.message.from_user.id)
    user_message = update.message.text

    today = str(datetime.date.today())

    # ---------- DAILY LIMIT ----------
    if user_id not in usage:
        usage[user_id] = {"date": today, "count": 0}

    if usage[user_id]["date"] != today:
        usage[user_id] = {"date": today, "count": 0}

    if usage[user_id]["count"] >= LIMIT:
        await update.message.reply_text(
            f"🚫 Free limit reached.\n\nUpgrade here:\n{PAYMENT_LINK}"
        )
        return

    usage[user_id]["count"] += 1

    # ---------- MEMORY ----------
    if user_id not in memory:
        memory[user_id] = []

    history = "\n".join(memory[user_id][-5:])
    is_new_user = len(memory[user_id]) == 0

    # ---------- ANALYSIS (WIZARD VICUNA) ----------
    analysis_prompt = f"""
You are a ruthless strategic analyst.

Understand:
- power dynamics
- manipulation
- corporate politics
- hidden motives

Break down reality brutally.

User history:
{history}

User message:
{user_message}

Analyze:
- true power structure
- hidden intentions
- risks
- opportunities
"""

    analysis_payload = {
        "model": "wizard-vicuna-7b",
        "prompt": analysis_prompt,
        "stream": False
    }

    try:
        analysis_res = requests.post(
            OLLAMA_URL, json=analysis_payload, headers=HEADERS, timeout=30
        )
        analysis_res.raise_for_status()
        analysis = analysis_res.json().get("response", "")

    except Exception as e:
        await update.message.reply_text(f"⚠️ Analysis Error: {str(e)}")
        return

    # ---------- FINAL RESPONSE (LLAMA3) ----------
    hook = ""
    if is_new_user:
        hook = "Most people fail because they misunderstand power.\n\n"

    final_prompt = f"""
You are Dravon Umbra, inspired by Niccolò Machiavelli.

{hook}

Respond in STRICT format:

⚔️ UNDERSTANDING THE SITUATION
- Clear breakdown

👑 WHO HOLDS POWER
- Identify authority

🧠 ENEMY MINDSET
- Explain opponent thinking OR possible scenario

🔮 NEXT PREDICTABLE MOVE
- Predict what happens next

♟️ STRATEGIC RESPONSE
- Give calculated, intelligent, non-emotional strategy

Rules:
- Be sharp
- No fluff
- Strategic tone

Analysis:
{analysis}

User message:
{user_message}
"""

    final_payload = {
        "model": "llama3",
        "prompt": final_prompt,
        "stream": False
    }

    try:
        final_res = requests.post(
            OLLAMA_URL, json=final_payload, headers=HEADERS, timeout=30
        )
        final_res.raise_for_status()
        final_answer = final_res.json().get("response", "")

    except Exception as e:
        await update.message.reply_text(f"⚠️ Response Error: {str(e)}")
        return

    # ---------- SAVE MEMORY ----------
    memory[user_id].append(f"User: {user_message}")
    memory[user_id].append(f"Dravon: {final_answer}")

    save_memory(memory)

    await update.message.reply_text(final_answer)

# ---------------- START BOT ----------------

app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("upgrade", upgrade))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, reply))

# ---------------- RAILWAY FIX ----------------

async def main():
    await app.initialize()
    await app.start()
    print("🚀 Dravon Umbra is LIVE on Railway")

    while True:
        await asyncio.sleep(100)

if __name__ == "__main__":
    asyncio.run(main())