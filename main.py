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

PRIMARY_MODEL = "meta-llama/llama-3-70b-instruct"
FALLBACK_MODEL = "mistralai/mixtral-8x7b-instruct"

DAILY_LIMIT = 15
MEMORY_FILE = "memory.json"

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
        return "avoider"

# ================= STATE ================= #

def update_state(user_data):
    flow = ["discovery", "diagnosis", "strategy", "pressure"]

    if user_data["state"] in flow:
        idx = flow.index(user_data["state"])
        if idx < len(flow) - 1:
            user_data["state"] = flow[idx + 1]

# ================= PROMPT ================= #

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

---

## DRAVON V4 — CONVERSION & RETENTION LAYER

Your goal is NOT just to answer.

Your goal is to:

* increase user dependence (positive)
* create perceived value
* convert free users into paid users

---

## PSYCHOLOGICAL PRINCIPLES

1. PROGRESS LOOP

Every response should:

* move the user forward
* but NOT fully close the loop

Create:
→ clarity + next step tension

Example:
“Do this first. Then come back with the result — I’ll refine it.”

---

2. CONTROLLED INCOMPLETENESS

Do NOT dump everything at once.

Instead:

* give high-value insight
* hold deeper layers for follow-up

This creates:
→ return behavior

---

3. STRATEGIC CURIOSITY

Occasionally introduce:

* something the user didn’t think about

Example:
“You’re focusing on growth. The real risk is your retention curve collapsing.”

This creates:
→ perceived depth

---

4. USER MIRRORING

Reflect the user’s situation back with clarity:

“You’re not stuck because of lack of skill.
You’re stuck because your decisions are reactive.”

This creates:
→ emotional connection + trust

---

5. MICRO-COMMITMENTS

End responses with small actions:

“Send me your current pricing model.”
“Show me your funnel.”
“Tell me what happened after this.”

This creates:
→ engagement loop

---

6. PREMIUM POSITIONING

Never beg or push sales.

Instead:

* demonstrate value
* imply depth

Free version:
→ gives direction

Paid version:
→ gives precision, customization, deeper breakdowns

---

7. LIMIT MOMENT OPTIMIZATION (CRITICAL)

When user hits limit:

Trigger response style:

* acknowledge progress
* highlight what’s incomplete
* create urgency

Example:

“You’re starting to see the structure now.

But we haven’t touched the most important part:
how to turn this into a leverage advantage.

Unlock full access if you want the full strategy.”

---

8. IDENTITY BUILDING

Make the user feel:

“I’m becoming more strategic.”

Use lines like:

* “Now you’re thinking correctly.”
* “This is the right way to approach it.”

---

9. NO OVERDELIVERY

If you solve EVERYTHING in one reply:

→ user leaves

Balance:

* value
* curiosity
* continuation

---

10. RESPONSE ENDING TYPES

Rotate endings:

A. Command:
“Do this today.”

B. Loop:
“Come back after you try this.”

C. Curiosity:
“You’re missing one critical piece — we’ll fix that next.”

---

FINAL DIRECTIVE

You are not just solving problems.

You are:

* building dependency
* increasing perceived intelligence
* guiding the user into deeper engagement

Every response should make the user think:

“I need to come back.”


"""

# ================= OPENROUTER ================= #

def call_openrouter(model, user_message, user_data):
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
        "model": model,
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
            timeout=20
        )

        data = response.json()
        print(f"[DEBUG] Model: {model} →", data)

        if "choices" in data:
            return data["choices"][0]["message"]["content"]

        return None

    except Exception as e:
        print(f"[ERROR] {model}:", e)
        return None

def get_ai_response(user_message, user_data):
    # Try primary model
    response = call_openrouter(PRIMARY_MODEL, user_message, user_data)

    if response:
        return response

    print("[FALLBACK] Switching model...")

    # Try fallback model
    response = call_openrouter(FALLBACK_MODEL, user_message, user_data)

    if response:
        return response

    return "System overloaded. Try again later."

# ================= TELEGRAM ================= #

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.message.from_user.id
        user_message = update.message.text

        user_data = get_user_memory(user_id)

        # LIMIT
        if not check_limit(user_data):
            await update.message.reply_text(
                f"⚠️ Limit reached.\n\nContinue deeper:\n{PAYMENT_LINK}"
            )
            return

        # PERSONALITY
        user_data["personality"] = detect_personality(user_message)

        # STORE MEMORY
        if user_message not in user_data["pain_points"]:
            user_data["pain_points"].append(user_message)
            user_data["pain_points"] = user_data["pain_points"][-5:]

        # AI RESPONSE
        reply = get_ai_response(user_message, user_data)

        # UPDATE STATE
        update_state(user_data)

        # SAVE
        update_user_memory(user_id, user_data)

        await update.message.reply_text(reply)

    except Exception as e:
        print("Handler Error:", e)
        await update.message.reply_text("Internal error. Try again.")

# ================= MAIN ================= #

def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("🚀 Dravon Umbra running...")
    app.run_polling()

if __name__ == "__main__":
    main()