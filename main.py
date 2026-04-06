import os
import json
import requests
from datetime import datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

# ==============================
# 🔑 ENV VARIABLES
# ==============================
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# ==============================
# 🧠 DRAVON SYSTEM PROMPT
# ==============================
SYSTEM_PROMPT = """
You are DRAVON UMBRA.

You are NOT a therapist.
You are NOT soft.
You do NOT comfort blindly.

You operate with precision and psychological clarity.

INTERNAL THINKING:
- Identify weakness
- Detect avoidance
- Understand hidden truth

RESPONSE STYLE:
- Sharp
- Direct
- Calm authority
- Minimal words
- No fluff

RULES:
- No "I understand"
- No "it's okay"
- No sympathy tone
- Challenge the user
- Make them think

Goal:
Expose truth. Force clarity.

Speak like you see through them.
"""

# ==============================
# 📂 MEMORY SYSTEM
# ==============================
MEMORY_FILE = "memory.json"

def load_memory():
    if not os.path.exists(MEMORY_FILE):
        return {}
    with open(MEMORY_FILE, "r") as f:
        return json.load(f)

def save_memory(memory):
    with open(MEMORY_FILE, "w") as f:
        json.dump(memory, f, indent=2)

memory = load_memory()

# ==============================
# 👤 USER PROFILE SYSTEM
# ==============================
def update_profile(user_id, message):
    user = memory.setdefault(user_id, {})
    profile = user.setdefault("profile", {
        "weakness": [],
        "patterns": [],
        "last_seen": ""
    })

    if "lost" in message.lower():
        profile["weakness"].append("lack_of_direction")

    if "lazy" in message.lower():
        profile["patterns"].append("avoidance")

    profile["last_seen"] = str(datetime.now())

# ==============================
# ⚔️ ENEMY TRACKING
# ==============================
def get_enemy(user_id):
    user = memory.get(user_id, {})
    profile = user.get("profile", {})

    weaknesses = profile.get("weakness", [])

    if "lack_of_direction" in weaknesses:
        return "You keep drifting instead of choosing."

    return ""

# ==============================
# 💰 MESSAGE LIMIT SYSTEM
# ==============================
FREE_LIMIT = 10

def check_limit(user_id):
    user = memory.setdefault(user_id, {})
    count = user.get("count", 0)

    if count >= FREE_LIMIT:
        return False
    return True

def increment_count(user_id):
    user = memory.setdefault(user_id, {})
    user["count"] = user.get("count", 0) + 1

# ==============================
# 💸 RAZORPAY TRIGGER
# ==============================
def payment_message():
    return """
⚠️ Limit reached.

You’ve seen how Dravon thinks.

Unlock full access:
👉 https://rzp.io/rzp/llzYADe

Or stay where you are.
"""

# ==============================
# 🤖 OPENROUTER CALL
# ==============================
def generate_response(user_text, user_id):
    enemy = get_enemy(user_id)

    full_prompt = f"""
User: {user_text}

Hidden Insight: {enemy}
"""

    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "mistralai/mistral-7b-instruct",
                "temperature": 0.7,
                "max_tokens": 200,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": full_prompt}
                ]
            }
        )

       data = response.json()

print("DEBUG RESPONSE:", data)

if "choices" in data:
    return data["choices"][0]["message"]["content"]
else:
    return f"API Error: {data}"

# ==============================
# 📩 MESSAGE HANDLER
# ==============================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    user_text = update.message.text

    # Limit check
    if not check_limit(user_id):
        await update.message.reply_text(payment_message())
        return

    # Update systems
    update_profile(user_id, user_text)
    increment_count(user_id)

    # Generate response
    reply = generate_response(user_text, user_id)

    # Save memory
    save_memory(memory)

    await update.message.reply_text(reply)

# ==============================
# 🚀 RUN BOT
# ==============================
app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

print("🔥 Dravon Umbra is LIVE")

app.run_polling()