# DRAVON UMBRA - V2 PRODUCTION MAIN (FULL UPGRADE)

import os
import json
import requests
import re
import asyncio
from datetime import datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
from telegram.constants import ChatAction

# ================= CONFIG ================= #

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
PAYMENT_LINK = "https://rzp.io/rzp/llzYADe"

PRIMARY_MODEL = "mistralai/mixtral-8x7b-instruct"
FALLBACK_MODEL = "meta-llama/llama-3-70b-instruct"

DAILY_LIMIT = 15
MEMORY_FILE = "memory.json"

# ================= PROMPT ================= #

def load_prompt():
    try:
        with open("prompt.txt", "r", encoding="utf-8") as f:
            return f.read()
    except:
        return "You are Dravon Umbra."

SYSTEM_PROMPT = load_prompt()

# ================= MEMORY ================= #

def load_memory():
    if not os.path.exists(MEMORY_FILE):
        return {}
    try:
        with open(MEMORY_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_memory(memory):
    with open(MEMORY_FILE, "w") as f:
        json.dump(memory, f, indent=2)

def get_user_memory(user_id):
    memory = load_memory()
    uid = str(user_id)

    if uid not in memory:
        memory[uid] = {
            "messages_today": 0,
            "last_reset": str(datetime.now().date()),
            "diagnostic": {
                "income": None,
                "runway": None,
                "idea": None,
                "risk": None,
                "time": None
            }
        }
        save_memory(memory)

    return memory[uid]

def update_user_memory(user_id, user_data):
    memory = load_memory()
    memory[str(user_id)] = user_data
    save_memory(memory)

# ================= LIMIT ================= #

def check_limit(user_data):
    today = str(datetime.now().date())

    if user_data["last_reset"] != today:
        user_data["messages_today"] = 0
        user_data["last_reset"] = today

    if user_data["messages_today"] >= DAILY_LIMIT:
        return False

    user_data["messages_today"] += 1
    return True

# ================= DIAGNOSTIC ================= #

HIGH_COMPLEX_KEYWORDS = [
    "quit", "career", "business", "money", "risk", "plan"
]

def detect_complexity(msg):
    return "high" if any(w in msg.lower() for w in HIGH_COMPLEX_KEYWORDS) else "low"

def evaluate_data(user_data):
    d = user_data["diagnostic"]
    score = sum([1 for v in d.values() if v]) * 0.2
    return score

def determine_mode(msg, user_data):
    complexity = detect_complexity(msg)
    score = evaluate_data(user_data)

    if complexity == "high" and score < 0.6:
        return "diagnostic"
    elif complexity == "high":
        return "execution"
    return "hybrid"

# ================= EXTRACTION ================= #

def extract_data(msg, user_data):
    d = user_data["diagnostic"]
    numbers = re.findall(r"\d+", msg)

    if "income" in msg and numbers:
        d["income"] = numbers[0]
    if "month" in msg and numbers:
        d["runway"] = numbers[0]
    if "idea" in msg or "business" in msg:
        d["idea"] = msg
    if "low" in msg:
        d["risk"] = "low"
    elif "high" in msg:
        d["risk"] = "high"
    if "hour" in msg and numbers:
        d["time"] = numbers[0]

    return user_data

# ================= QUESTIONS ================= #

def generate_questions(user_data):
    d = user_data["diagnostic"]
    q = []

    if not d.get("income"): q.append("What is your monthly income?")
    if not d.get("runway"): q.append("How many months can you survive without income?")
    if not d.get("idea"): q.append("Do you have a business or income idea?")
    if not d.get("risk"): q.append("Your risk tolerance? low / medium / high")
    if not d.get("time"): q.append("How many hours daily can you invest?")

    return q

# ================= RESPONSES ================= #

def diagnostic_response(q):
    q_text = "\n".join([f"{i+1}. {x}" for i,x in enumerate(q)])
    return f"⚔️ POSITION\nNeed more data.\n\n🧠 MISSING\n{q_text}\n\nAnswer these."

def hybrid_response(q):
    q_text = "\n".join([f"{i+1}. {x}" for i,x in enumerate(q)])
    return f"⚔️ POSITION\nEarly decision likely wrong.\n\n🧠 NEED\n{q_text}"

# ================= AI ENGINE ================= #

def enforce_quality(reply):
    weak = ["it depends","you could","consider"]
    for w in weak:
        reply = reply.replace(w, "")
    return reply.strip()


def build_prompt(user_message, user_data):
    d = user_data["diagnostic"]

    return f"""
You are Dravon Umbra.

You MUST take a position.

Context:
Income: {d['income']}
Runway: {d['runway']}
Risk: {d['risk']}
Time: {d['time']}

Think:
- Real problem
- Constraints
- 3 paths
- Choose best
- Execution steps

User:
{user_message}

Format:
⚔️ POSITION
🧠 REALITY
🎯 DECISION
⚙️ EXECUTION
⚠️ RISK
⚔️ FINAL
"""


def call_ai(prompt):
    headers = {"Authorization": f"Bearer {OPENROUTER_API_KEY}"}

    payload = {
        "model": PRIMARY_MODEL,
        "messages": [{"role":"user","content":prompt}]
    }

    res = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload)

    if res.status_code == 200:
        return res.json()["choices"][0]["message"]["content"]

    return "Error"

# ================= STREAM ================= #

async def stream(update, context, text):
    chat_id = update.effective_chat.id
    parts = text.split("\n")

    msg = None
    current = ""

    for i, p in enumerate(parts):
        current += p + "\n"
        await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
        await asyncio.sleep(0.7)

        if i == 0:
            msg = await context.bot.send_message(chat_id, current)
        else:
            try:
                await context.bot.edit_message_text(chat_id=chat_id, message_id=msg.message_id, text=current)
            except:
                msg = await context.bot.send_message(chat_id, current)

# ================= HANDLER ================= #

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    msg = update.message.text.lower()

    user_data = get_user_memory(user_id)

    if not check_limit(user_data):
        await update.message.reply_text(f"Limit reached\n{PAYMENT_LINK}")
        return

    user_data = extract_data(msg, user_data)
    mode = determine_mode(msg, user_data)
    questions = generate_questions(user_data)

    if mode == "diagnostic":
        await update.message.reply_text(diagnostic_response(questions))

    elif mode == "hybrid":
        await update.message.reply_text(hybrid_response(questions))

    else:
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
        prompt = build_prompt(msg, user_data)
        reply = call_ai(prompt)
        reply = enforce_quality(reply)
        await stream(update, context, reply)

    update_user_memory(user_id, user_data)

# ================= MAIN ================= #

def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("Dravon V2 Running...")
    app.run_polling()

if __name__ == "__main__":
    main()
