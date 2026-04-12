# DRAVON UMBRA - PRODUCTION MAIN.PY (UPGRADED WITH DIAGNOSTIC ENGINE)

import os
import json
import requests
import re
from datetime import datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

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
            "state": "discovery",
            "personality": "unknown",

            "identity": {
                "role": "",
                "goals": [],
                "stage": ""
            },

            "behavior": {
                "risk_appetite": "",
                "decision_style": ""
            },

            "history": {
                "key_events": [],
                "patterns": []
            },

            "pain_points": [],

            # NEW: diagnostic variables
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

# ================= DIAGNOSTIC ENGINE ================= #

HIGH_COMPLEX_KEYWORDS = [
    "quit", "career", "business", "money", "start",
    "risk", "decision", "future", "plan"
]

def detect_complexity(user_input):
    for word in HIGH_COMPLEX_KEYWORDS:
        if word in user_input.lower():
            return "high"
    return "low"

def evaluate_data(user_data):
    d = user_data["diagnostic"]
    score = 0
    if d.get("income"): score += 0.2
    if d.get("runway"): score += 0.2
    if d.get("idea"): score += 0.2
    if d.get("risk"): score += 0.2
    if d.get("time"): score += 0.2
    return score

def determine_mode(user_input, user_data):
    complexity = detect_complexity(user_input)
    data_score = evaluate_data(user_data)

    if complexity == "high" and data_score < 0.6:
        return "diagnostic"
    elif complexity == "high" and data_score >= 0.6:
        return "execution"
    else:
        return "hybrid"

# ================= MEMORY EXTRACTION ================= #

def extract_insights(message, user_data):
    msg = message.lower()

    # existing
    if "startup" in msg or "founder" in msg:
        user_data["identity"]["role"] = "founder"
    elif "job" in msg or "manager" in msg:
        user_data["identity"]["role"] = "employee"

    if "grow" in msg or "scale" in msg:
        if "growth" not in user_data["identity"]["goals"]:
            user_data["identity"]["goals"].append("growth")

    # diagnostic extraction
    numbers = re.findall(r"\d+", msg)

    if "income" in msg or "salary" in msg:
        if numbers:
            user_data["diagnostic"]["income"] = numbers[0]

    if "month" in msg or "savings" in msg:
        if numbers:
            user_data["diagnostic"]["runway"] = numbers[0]

    if "idea" in msg or "business" in msg:
        user_data["diagnostic"]["idea"] = message

    if "low" in msg and "risk" in msg:
        user_data["diagnostic"]["risk"] = "low"
    elif "medium" in msg:
        user_data["diagnostic"]["risk"] = "medium"
    elif "high" in msg:
        user_data["diagnostic"]["risk"] = "high"

    if "hour" in msg or "time" in msg:
        if numbers:
            user_data["diagnostic"]["time"] = numbers[0]

    return user_data

# ================= QUESTION ENGINE ================= #

def generate_questions(user_data):
    d = user_data["diagnostic"]
    questions = []

    if not d.get("income"):
        questions.append("What is your monthly income?")
    if not d.get("runway"):
        questions.append("How many months can you survive without income?")
    if not d.get("idea"):
        questions.append("Do you have a specific idea or income path?")
    if not d.get("risk"):
        questions.append("What’s your risk tolerance: low, medium, or high?")
    if not d.get("time"):
        questions.append("How much time can you invest daily?")

    return questions

# ================= RESPONSE MODES ================= #

def diagnostic_response(questions):
    return f"""
⚔️ POSITION
You’re asking for a decision without enough data.

🧠 MISSING VARIABLES
{"\n".join([str(i+1)+'. '+q for i,q in enumerate(questions)])}

🎯 NEXT STEP
Answer these. Then I’ll give you a precise move.
"""


def hybrid_response(questions):
    return f"""
⚔️ POSITION
Based on limited data, quitting immediately is usually a mistake.

⚠️ LIMITATION
This is a surface-level call. Precision requires more data.

🧠 I NEED:
{"\n".join([str(i+1)+'. '+q for i,q in enumerate(questions)])}

🎯 NEXT STEP
Answer these. Then I refine this into a precise strategy.
"""


def execution_gate():
    return f"""
You now have enough data for a full execution strategy.

Unlock full plan:
{PAYMENT_LINK}
"""

# ================= OPENROUTER ================= #

def call_openrouter(model, user_message, user_data, retries=3):
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "system", "content": f"User Profile: {json.dumps(user_data)}"},
        {"role": "user", "content": user_message}
    ]

    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.7
    }

    for _ in range(retries):
        try:
            res = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=40
            )

            if res.status_code == 200:
                return res.json()["choices"][0]["message"]["content"]

        except Exception:
            pass

    return "System busy. Try again."

# ================= TELEGRAM ================= #

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_message = update.message.text

    user_data = get_user_memory(user_id)

    if not check_limit(user_data):
        await update.message.reply_text(f"Limit reached.\n\nUpgrade: {PAYMENT_LINK}")
        return

    if user_message.lower() in ["hi", "hello", "hey"]:
        await update.message.reply_text("Good. What are we solving today?")
        return

    user_data = extract_insights(user_message, user_data)

    mode = determine_mode(user_message, user_data)
    questions = generate_questions(user_data)

    if mode == "diagnostic":
        reply = diagnostic_response(questions)

    elif mode == "hybrid":
        reply = hybrid_response(questions)

    elif mode == "execution":
        reply = execution_gate()

    update_user_memory(user_id, user_data)

    await update.message.reply_text(reply)

# ================= MAIN ================= #

def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Dravon running...")
    app.run_polling()

if __name__ == "__main__":
    main()
