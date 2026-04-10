import os
import json
import requests
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

# ================= PROMPT LOAD ================= #

def load_prompt():
    try:
        with open("prompt.txt", "r", encoding="utf-8") as f:
            return f.read()
    except:
        return "You are Dravon Umbra."

SYSTEM_PROMPT = load_prompt()

# ================= MEMORY ================= #

def load_memory():
    try:
        if not os.path.exists(MEMORY_FILE):
            return {}
        with open(MEMORY_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_memory(memory):
    try:
        with open(MEMORY_FILE, "w") as f:
            json.dump(memory, f, indent=2)
    except Exception as e:
        print("Memory Save Error:", e)

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

            "pain_points": []
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

# ================= PERSONALITY ================= #

def detect_personality(message):
    msg = message.lower()

    if any(x in msg for x in ["lost", "confused", "direction"]):
        return "drifter"
    elif any(x in msg for x in ["angry", "hate", "frustrated"]):
        return "reactor"
    elif any(x in msg for x in ["how", "what should"]):
        return "seeker"
    elif any(x in msg for x in ["plan", "strategy", "growth"]):
        return "strategist"
    else:
        return "neutral"

# ================= V5 MEMORY EXTRACTION ================= #

def extract_insights(user_message, user_data):
    msg = user_message.lower()

    # ROLE
    if "startup" in msg or "founder" in msg:
        user_data["identity"]["role"] = "founder"
    elif "job" in msg or "manager" in msg:
        user_data["identity"]["role"] = "employee"

    # GOALS
    if "grow" in msg or "scale" in msg:
        if "growth" not in user_data["identity"]["goals"]:
            user_data["identity"]["goals"].append("growth")

    # RISK
    if "safe" in msg:
        user_data["behavior"]["risk_appetite"] = "low"
    elif "aggressive" in msg:
        user_data["behavior"]["risk_appetite"] = "high"

    # DECISION STYLE
    if "confused" in msg or "not sure" in msg:
        user_data["behavior"]["decision_style"] = "reactive"

    return user_data

# ================= STATE ================= #

def update_state(user_data):
    flow = ["discovery", "diagnosis", "strategy", "pressure"]

    if user_data["state"] in flow:
        idx = flow.index(user_data["state"])
        if idx < len(flow) - 1:
            user_data["state"] = flow[idx + 1]

# ================= OPENROUTER ================= #

def call_openrouter(model, user_message, user_data, retries=3):
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "system",
            "content": f"""
User Intelligence Profile:

Role: {user_data['identity']['role']}
Goals: {user_data['identity']['goals']}
Stage: {user_data['identity']['stage']}

Risk Appetite: {user_data['behavior']['risk_appetite']}
Decision Style: {user_data['behavior']['decision_style']}

Patterns: {user_data['history']['patterns']}
Recent Pain Points: {user_data['pain_points']}
"""
        },
        {"role": "user", "content": user_message}
    ]

    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.7
    }

    for attempt in range(retries):
        try:
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=40
            )

            if response.status_code == 200:
                data = response.json()
                if "choices" in data:
                    return data["choices"][0]["message"]["content"]

            print(f"[Retry {attempt+1}] {model} Failed:", response.text)

        except Exception as e:
            print(f"[ERROR Attempt {attempt+1}]:", e)

    return None

def get_ai_response(user_message, user_data):
    response = call_openrouter(PRIMARY_MODEL, user_message, user_data)

    if response:
        return response

    print("[FALLBACK] Switching model...")

    response = call_openrouter(FALLBACK_MODEL, user_message, user_data)

    if response:
        return response

    return """[Position]
System instability detected — not your input.

[Reality]
Model failed due to load or API limits.

[Move]
Wait 10–20 seconds and retry.

[Final Command]
Send your message again."""
    
# ================= TELEGRAM ================= #

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.message.from_user.id
        user_message = update.message.text

        user_data = get_user_memory(user_id)

        # LIMIT
        if not check_limit(user_data):
            await update.message.reply_text(
                f"""⚠️ Limit reached.

You’re starting to see the structure.

But the real leverage layer is next.

Unlock full access:
{PAYMENT_LINK}"""
            )
            return

        # PERSONALITY
        user_data["personality"] = detect_personality(user_message)

        # V5 EXTRACTION
        user_data = extract_insights(user_message, user_data)

        # MEMORY STORE
        if user_message not in user_data["pain_points"]:
            user_data["pain_points"].append(user_message)
            user_data["pain_points"] = user_data["pain_points"][-5:]

        # AI RESPONSE
        reply = get_ai_response(user_message, user_data)

        # STATE UPDATE
        update_state(user_data)

        # SAVE
        update_user_memory(user_id, user_data)

        await update.message.reply_text(reply)

    except Exception as e:
        print("Handler Error:", e)
        await update.message.reply_text("Internal error. Try again.")

# ================= MAIN ================= #

def main():
    if not OPENROUTER_API_KEY or not TELEGRAM_TOKEN:
        print("❌ Missing environment variables!")
        return

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("🚀 Dravon Umbra running...")
    app.run_polling()

if __name__ == "__main__":
    main()