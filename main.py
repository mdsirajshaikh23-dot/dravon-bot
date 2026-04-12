# DRAVON UMBRA - FINAL PRODUCTION MAIN (ALL SYSTEMS INTEGRATED)

import os
import json
import re
import asyncio
import requests
from datetime import datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
from telegram.constants import ChatAction

# ================= CONFIG ================= #

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
PAYMENT_LINK = "https://rzp.io/rzp/llzYADe"

MODEL = "mistralai/mixtral-8x7b-instruct"
MEMORY_FILE = "memory.json"
DAILY_LIMIT = 15

# ================= MEMORY ================= #

def load_memory():
    if not os.path.exists(MEMORY_FILE): return {}
    with open(MEMORY_FILE, "r") as f: return json.load(f)

def save_memory(mem):
    with open(MEMORY_FILE, "w") as f: json.dump(mem, f, indent=2)

def get_user(user_id):
    mem = load_memory()
    uid = str(user_id)

    if uid not in mem:
        mem[uid] = {
            "messages_today": 0,
            "last_reset": str(datetime.now().date()),

            "conversation": {"state": "free_chat"},

            "diagnostic": {
                "income": None,
                "runway": None,
                "idea": None,
                "risk": None,
                "time": None
            },

            "personality": {"type": "unknown", "tone": "neutral"},

            "behavior_log": [],
            "patterns": {"indecision": 0, "switching": 0},

            "monetization": {"score": 0, "stage": "free"}
        }
        save_memory(mem)

    return mem[uid]

def update_user(user_id, data):
    mem = load_memory()
    mem[str(user_id)] = data
    save_memory(mem)

# ================= LIMIT ================= #

def check_limit(user):
    today = str(datetime.now().date())
    if user["last_reset"] != today:
        user["messages_today"] = 0
        user["last_reset"] = today

    if user["messages_today"] >= DAILY_LIMIT:
        return False

    user["messages_today"] += 1
    return True

# ================= INTENT ================= #

def classify_intent(msg):
    msg = msg.lower()
    if any(x in msg for x in ["why", "what are you", "how do you"]): return "meta"
    if any(x in msg for x in ["should i", "quit", "start", "decision"]): return "decision"
    return "normal"

# ================= EXTRACTION ================= #

def extract(msg, user):
    d = user["diagnostic"]
    nums = re.findall(r"\d+", msg)

    if "income" in msg and nums: d["income"] = nums[0]
    if "month" in msg and nums: d["runway"] = nums[0]
    if "idea" in msg: d["idea"] = msg
    if "low" in msg: d["risk"] = "low"
    if "high" in msg: d["risk"] = "high"
    if "hour" in msg and nums: d["time"] = nums[0]

    return user

# ================= PERSONALITY ================= #

def detect_personality(msg, user):
    if "confused" in msg: user["personality"]["type"] = "emotional"
    elif "fast" in msg: user["personality"]["type"] = "action"
    elif "analyze" in msg: user["personality"]["type"] = "analytical"
    return user

# ================= BEHAVIOR ================= #

def log_behavior(msg, user):
    user["behavior_log"].append(msg)
    user["behavior_log"] = user["behavior_log"][-20:]
    return user


def detect_patterns(user):
    log = user["behavior_log"]
    if sum("should" in m for m in log) >= 3:
        user["patterns"]["indecision"] += 1
    return user

# ================= MONETIZATION ================= #

def update_value(msg, user):
    if len(msg) > 20: user["monetization"]["score"] += 1
    if "should" in msg: user["monetization"]["score"] += 2

    s = user["monetization"]["score"]
    if s >= 6: user["monetization"]["stage"] = "ready"
    elif s >= 3: user["monetization"]["stage"] = "warm"

    return user

# ================= QUESTIONS ================= #

def questions(user):
    d = user["diagnostic"]
    q = []
    if not d["income"]: q.append("Monthly income?")
    if not d["runway"]: q.append("Savings runway (months)?")
    if not d["idea"]: q.append("Any business idea?")
    return q

# ================= AI ================= #

def build_prompt(msg, user):
    d = user["diagnostic"]
    return f"""
You are Dravon Umbra.
Take a position.

Income:{d['income']} Runway:{d['runway']} Risk:{d['risk']}

User:{msg}

Format:
⚔️ POSITION
🧠 REALITY
🎯 DECISION
⚙️ EXECUTION
⚠️ RISK
⚔️ FINAL
"""


def call_ai(prompt):
    res = requests.post("https://openrouter.ai/api/v1/chat/completions",
        headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}"},
        json={"model": MODEL, "messages": [{"role":"user","content":prompt}]})

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
        await asyncio.sleep(0.6)

        if i == 0:
            msg = await context.bot.send_message(chat_id, current)
        else:
            try:
                await context.bot.edit_message_text(chat_id=chat_id, message_id=msg.message_id, text=current)
            except:
                msg = await context.bot.send_message(chat_id, current)

# ================= VIRAL ================= #

def viral(reply):
    lines = reply.split("\n")
    key = "\n".join(lines[:3])
    return reply + f"\n\n🔥\n{key}\n— Dravon"

# ================= HANDLER ================= #

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    msg = update.message.text.lower()

    user = get_user(user_id)

    if not check_limit(user):
        await update.message.reply_text(f"Limit hit\n{PAYMENT_LINK}")
        return

    intent = classify_intent(msg)

    user = extract(msg, user)
    user = detect_personality(msg, user)
    user = log_behavior(msg, user)
    user = detect_patterns(user)
    user = update_value(msg, user)

    if intent == "meta":
        await update.message.reply_text("I ask to reduce uncertainty.")
        return

    qs = questions(user)

    if qs:
        await update.message.reply_text("\n".join(qs))
    else:
        prompt = build_prompt(msg, user)
        reply = call_ai(prompt)
        reply = viral(reply)
        await stream(update, context, reply)

    update_user(user_id, user)

# ================= MAIN ================= #

def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))
    print("Dravon Final Running...")
    app.run_polling()

if __name__ == "__main__":
    main()
