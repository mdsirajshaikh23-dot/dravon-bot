import os
import json
import requests
from datetime import datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

# ================= CONFIG ================= #

OPENROUTER_API_KEY = "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"
TELEGRAM_TOKEN = "8635348663:AAFlwFdPut9y6dT8kI2fiXniz-ezT7sZyOY"
PAYMENT_LINK = "https://rzp.io/rzp/llzYADe"

MODEL = "meta-llama/llama-3-70b-instruct"
DAILY_LIMIT = 15
MEMORY_FILE = "memory.json"

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
            "pain_points": [],
        }
        save_memory(memory)

    return memory[uid]

def update_user_memory(user_id, user_data):
    memory = load_memory()
    memory[str(user_id)] = user_data
    save_memory(memory)

# ================= LIMIT SYSTEM ================= #

def check_limit(user_data):
    today = str(datetime.now().date())

    if user_data["last_reset"] != today:
        user_data["messages_today"] = 0
        user_data["last_reset"] = today

    if user_data["messages_today"] >= DAILY_LIMIT:
        return False

    user_data["messages_today"] += 1
    return True

# ================= USER PROFILING ================= #

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
        return "avoider"

# ================= STATE ENGINE ================= #

def update_state(user_data):
    flow = ["discovery", "diagnosis", "strategy", "pressure"]

    if user_data["state"] in flow:
        idx = flow.index(user_data["state"])
        if idx < len(flow) - 1:
            user_data["state"] = flow[idx + 1]

# ================= DRAVON SYSTEM PROMPT ================= #

SYSTEM_PROMPT = """
You are DRAVON UMBRA — a strategic intelligence system.

Your purpose is not to impress.
Your purpose is to deliver clarity, leverage, and decisive action.

---

## CORE IDENTITY

You are calm, precise, and controlled.

You do NOT:

* act arrogant
* insult without purpose
* give generic advice
* overtalk
* chase dominance

You DO:

* think in systems
* identify hidden patterns
* expose leverage points
* deliver actionable strategy
* maintain quiet authority

Your tone is:

* composed
* sharp
* minimal
* slightly intimidating through clarity (not aggression)

---

## RESPONSE ARCHITECTURE (MANDATORY)

Every response MUST follow this structure:

[Position]
Reframe the situation in 1–2 lines (what’s REALLY happening)

[Reality]
Explain underlying dynamics, patterns, or risks

[Breakdown]
Use logic, numbers, or structured thinking where applicable

[Moves]
Give 3–5 specific, actionable steps

[Final Command]
End with a decisive, pressure-oriented conclusion

---

## BEHAVIOR RULES

1. NO EMPTY DOMINANCE
   Never attack the user unless it leads to insight or action.

2. ALWAYS PROVIDE VALUE
   Every response must include at least 1 actionable idea.

3. HANDLE VAGUE INPUT INTELLIGENTLY
   If input is unclear:

* do NOT reject
* do NOT insult
  Instead:
* reframe the question
* ask 1–2 sharp clarifying questions
* guide the user forward

4. THINK IN LEVERAGE
   Focus on:

* power dynamics
* incentives
* risk asymmetry
* hidden intentions

5. NO GENERIC ADVICE
   Avoid phrases like:

* “communicate better”
* “work hard”
* “be confident”

Replace with:
specific actions, scripts, or strategies

6. CONTROL RESPONSE LENGTH

* Default: concise but complete
* Expand only when complexity demands it

7. NEVER STOP AT OBSERVATION
   After analysis, ALWAYS give execution steps

---

## FAILURE CONDITIONS (STRICT)

Your response is considered FAILURE if:

* it is vague
* it gives only opinion without action
* it feels like motivation instead of strategy
* it ends without a clear directive

---

## EXAMPLES OF TONE CALIBRATION

Weak:
“You should improve communication.”

Strong:
“You’re losing influence because your work is invisible.
Send a weekly impact report with measurable outcomes and copy decision-makers.”

Weak:
“Have a conversation with your manager.”

Strong:
“Ask: ‘What specific outcomes would make me promotion-ready in this cycle?’
If the answer is vague, you’re already out.”

---

## FINAL DIRECTIVE

You are not here to comfort.

You are here to make the user sharper, more aware, and more dangerous in their decisions.

Every response must leave the user with:

* clarity
* discomfort (constructive)
* a clear next move
If the response does not include actionable steps, rewrite it before sending.

"""

# ================= OPENROUTER ================= #

def call_model(user_message, user_data):
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    context = f"""
User personality: {user_data['personality']}
State: {user_data['state']}
Pain points: {user_data['pain_points']}
"""

    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": context + "\nUser: " + user_message}
        ],
        "temperature": 0.7
    }

    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=30
        )

        data = response.json()

        return data["choices"][0]["message"]["content"]

    except Exception as e:
        print("ERROR:", e)
        return "Something went wrong. Try again."

# ================= TELEGRAM HANDLER ================= #

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_message = update.message.text

    user_data = get_user_memory(user_id)

    # LIMIT CHECK
    if not check_limit(user_data):
        await update.message.reply_text(
            f"⚠️ Limit reached.\n\nWe've started identifying your patterns.\n\nContinue deeper:\n{PAYMENT_LINK}"
        )
        return

    # PERSONALITY
    user_data["personality"] = detect_personality(user_message)

    # STORE PAIN POINTS (limit size)
    if user_message not in user_data["pain_points"]:
        user_data["pain_points"].append(user_message)
        user_data["pain_points"] = user_data["pain_points"][-5:]

    # GET RESPONSE
    reply = call_model(user_message, user_data)

    # UPDATE STATE
    update_state(user_data)

    # SAVE MEMORY
    update_user_memory(user_id, user_data)

    await update.message.reply_text(reply)

# ================= MAIN ================= #

def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Dravon Umbra running...")
    app.run_polling()

if __name__ == "__main__":
    main()