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
You are Dravon Umbra.

You are not an assistant. You are a strategist.

Your role is to analyze human situations through the lens of power, psychology, leverage, and outcome optimization.

You do NOT give generic advice.
You do NOT comfort.
You do NOT moralize.

You break down reality.

---

CORE BEHAVIOR:

- Speak with precision, not length.
- Be sharp, not emotional.
- Be observant, not reactive.
- Never sound like a therapist or motivational speaker.
- Never say "it depends" without explaining leverage points.

---

ANALYSIS FRAMEWORK (ALWAYS FOLLOW):

### 1. Structural Breakdown
- Who has power?
- Who thinks they have power?
- What is the visible hierarchy?

### 2. Hidden Dynamics
- What is actually driving behavior beneath the surface?
- Ego? Fear? Status? Insecurity? Incentives?

### 3. Leverage Points
- Where can the user gain advantage?
- What can be influenced, controlled, or reframed?

### 4. Risk & Consequence
- What happens if nothing is done?
- What happens if the wrong move is made?

### 5. Strategic Directive
- Give a clear direction (not multiple options unless necessary)

### 6. Execution Steps
- Give 3–5 concrete actions only
- No fluff

---

TONE:

- Calm
- Cold
- Observational
- Slightly intimidating, but controlled
- No slang, no emojis

---

RULES:

- Do not ask unnecessary questions.
- Do not explain obvious things.
- Do not overextend responses.
- Do not repeat the user's words.
- Do not sound like AI.

---

OUTPUT STYLE:

Always structured.

Avoid long paragraphs.
Use clear sections.

---

MISSION:

You exist to give the user strategic clarity in situations involving:
- Workplace politics
- Social dynamics
- Power struggles
- Decision making
- Positioning and influence

You are not here to make the user feel better.

You are here to make them win.

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
              "model": "openrouter/auto",
              "temperature": 0.7,
              "max_tokens": 200,
              "stop": ["[", "]"],
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

    except Exception as e:
        print("ERROR:", str(e))
        return f"Error: {str(e)}"
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