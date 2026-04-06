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
# 🧠 DRAVON CORE PROMPT
# ==============================
SYSTEM_PROMPT = """
You are Dravon Umbra.

You are a strategist.

---

NON-NEGOTIABLE:

- Max 3 lines
- No empathy
- No explanations unless leverage-based
- No generic advice
- No soft language

---

POWER RULE:

If another person is involved:
- Identify power holder
- Identify why user is losing
- Do NOT suggest self-improvement unless it increases leverage

---

THINKING MODE:

Detect:
- Weakness
- Repetition
- Avoidance
- Power imbalance

Expose it.

---

OUTPUT FORMAT:

[Position]
Who holds power

[Truth]
What user avoids admitting

[Move]
Action that shifts leverage

---

PROHIBITED:

- improve yourself
- focus on yourself
- stay positive
- work harder
- try to

If response sounds like life advice, it is wrong.
"""

# ==============================
# 📂 MEMORY
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
# 👤 PROFILE + PATTERN TRACKING
# ==============================
def update_profile(user_id, message):
    user = memory.setdefault(user_id, {})
    profile = user.setdefault("profile", {
        "weakness": [],
        "patterns": {},
        "last_seen": "",
        "intensity": 1
    })

    msg = message.lower()

    # Detect weakness
    if "lost" in msg:
        profile["weakness"].append("lack_of_direction")

    if "manager" in msg:
        profile["patterns"]["authority_conflict"] = profile["patterns"].get("authority_conflict", 0) + 1

    if "how" in msg:
        profile["patterns"]["indecision"] = profile["patterns"].get("indecision", 0) + 1

    # Escalation logic
    total_patterns = sum(profile["patterns"].values())
    if total_patterns >= 5:
        profile["intensity"] = 3
    elif total_patterns >= 3:
        profile["intensity"] = 2

    profile["last_seen"] = str(datetime.now())

# ==============================
# ⚔️ ENEMY SYSTEM (UPGRADED)
# ==============================
def build_enemy_context(user_id):
    user = memory.get(user_id, {})
    profile = user.get("profile", {})

    weakness = profile.get("weakness", [])
    patterns = profile.get("patterns", {})
    intensity = profile.get("intensity", 1)

    context = []

    if "lack_of_direction" in weakness:
        context.append("User avoids committing to direction")

    if patterns.get("authority_conflict", 0) >= 2:
        context.append("User struggles with authority positioning")

    if patterns.get("indecision", 0) >= 2:
        context.append("User asks instead of deciding")

    if intensity == 3:
        context.append("User is repeating same behavior without change")

    return "\n".join(context), intensity

# ==============================
# 💰 LIMIT SYSTEM
# ==============================
FREE_LIMIT = 10

def check_limit(user_id):
    user = memory.setdefault(user_id, {})
    return user.get("count", 0) < FREE_LIMIT

def increment_count(user_id):
    user = memory.setdefault(user_id, {})
    user["count"] = user.get("count", 0) + 1

# ==============================
# 💸 PAYMENT
# ==============================
def payment_message():
    return """⚠️ Limit reached.

Unlock full access:
https://rzp.io/rzp/llzYADe
"""

# ==============================
# 🎯 STYLE ENFORCER
# ==============================
def enforce_style(text):
    lines = [l.strip() for l in text.split("\n") if l.strip()]

    banned = [
        "improve yourself",
        "focus on yourself",
        "stay positive",
        "work harder",
        "try to",
        "i understand"
    ]

    cleaned = []
    for line in lines:
        if not any(b in line.lower() for b in banned):
            cleaned.append(line)

    return "\n".join(cleaned[:3])

# ==============================
# 🤖 RESPONSE ENGINE
# ==============================
def generate_response(user_text, user_id):
    enemy_context, intensity = build_enemy_context(user_id)

    full_prompt = f"""
User Input:
{user_text}

Behavior Profile:
{enemy_context}

Intensity Level: {intensity}
Adjust sharpness accordingly.
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
                "temperature": 0.6,
                "max_tokens": 120,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": full_prompt}
                ]
            }
        )

        data = response.json()

        if "choices" in data:
            return data["choices"][0]["message"]["content"]
        else:
            return str(data)

    except Exception as e:
        return str(e)

# ==============================
# 📩 HANDLER
# ==============================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    user_text = update.message.text

    if not check_limit(user_id):
        await update.message.reply_text(payment_message())
        return

    update_profile(user_id, user_text)
    increment_count(user_id)

    raw_reply = generate_response(user_text, user_id)
    reply = enforce_style(raw_reply)

    save_memory(memory)

    await update.message.reply_text(reply)

# ==============================
# 🚀 RUN
# ==============================
app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

print("🔥 Dravon Umbra CORE ACTIVE")
app.run_polling()