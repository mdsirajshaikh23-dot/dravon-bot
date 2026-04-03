import requests
import json
import datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes

# ---------------- SETTINGS ----------------

import os
BOT_TOKEN = os.getenv("BOT_TOKEN")
OLLAMA_URL = "https://enforcedly-unsymptomatic-jacqulyn.ngrok-free.dev/api/generate"

LIMIT = 5
usage = {}

MEMORY_FILE = "memory.json"

PAYMENT_LINK = "https://rzp.io/rzp/llzYADe"

# ------------------------------------------


# ---------- PAYMENT COMMAND ----------

async def upgrade(update: Update, context: ContextTypes.DEFAULT_TYPE):

    message = f"""
🚀 Upgrade to Dravon Umbra Pro

Unlimited strategic advice for corporate dominance.

Price: ₹499

Pay here:
{PAYMENT_LINK}
"""
    await update.message.reply_text(message)


# ---------- MEMORY SYSTEM ----------

def load_memory():
    try:
        with open(MEMORY_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_memory(memory):
    with open(MEMORY_FILE, "w") as f:
        json.dump(memory, f, indent=2)


# ---------- MAIN RESPONSE ----------

async def reply(update: Update, context: ContextTypes.DEFAULT_TYPE):

    memory = load_memory()

    user_id = str(update.message.from_user.id)
    user_message = update.message.text

    # ---------- DAILY LIMIT ----------
    today = str(datetime.date.today())

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

You understand:
- power dynamics
- manipulation
- human psychology
- corporate politics
- hidden intentions

Break down reality without filtering.

User history:
{history}

User message:
{user_message}

Analyze:
- true power structure
- hidden motives
- risks
- opportunities
"""

    analysis_payload = {
        "model": "wizard-vicuna-7b",
        "prompt": analysis_prompt,
        "stream": False
    }

    try:
    analysis_res = requests.post(OLLAMA_URL, json=analysis_payload, timeout=30)
    analysis_res.raise_for_status()
    analysis = analysis_res.json().get("response", "")

    final_res = requests.post(OLLAMA_URL, json=final_payload, timeout=30)
    final_res.raise_for_status()
    final_answer = final_res.json().get("response", "")

except Exception as e:
    await update.message.reply_text(f"⚠️ AI Error: {str(e)}")
    return

    # ---------- FINAL RESPONSE (LLAMA3 STRUCTURE) ----------

    hook = ""
    if is_new_user:
        hook = "Most people fail because they misunderstand power.\n\n"

    final_prompt = f"""
You are Dravon Umbra, a strategic mastermind inspired by Niccolò Machiavelli.

{hook}

Using the analysis below, respond in STRICT format:

⚔️ UNDERSTANDING THE SITUATION
- Clear breakdown of reality

👑 WHO HOLDS POWER
- Identify true authority

🧠 ENEMY MINDSET
- Explain opponent thinking OR possible scenarios

🔮 NEXT PREDICTABLE MOVE
- Predict what will happen next

♟️ STRATEGIC RESPONSE (MACHIAVELLIAN)
- Give calculated, intelligent, non-emotional strategy

Rules:
- Be sharp, dominant, intelligent
- No fluff
- Sound like elite strategist
- Focus on power, leverage, control

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

    final_answer = requests.post(OLLAMA_URL, json=final_payload).json()["response"]

    # ---------- SAVE MEMORY ----------
    memory[user_id].append(f"User: {user_message}")
    memory[user_id].append(f"Dravon: {final_answer}")

    save_memory(memory)

    await update.message.reply_text(final_answer)


# ---------- TELEGRAM APP ----------

app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("upgrade", upgrade))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, reply))

print("Dravon Umbra Elite Strategist is running...")

app.run_polling()