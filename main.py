import json
import os
from datetime import datetime
import requests

# =========================
# CONFIG
# =========================

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
MODEL = "openrouter/auto"

PROMPT_FILE = "prompt.txt"
MEMORY_FILE = "memory.json"

# =========================
# LOAD SYSTEM PROMPT
# =========================

def load_prompt():
    with open(PROMPT_FILE, "r", encoding="utf-8") as f:
        return f.read()

SYSTEM_PROMPT = load_prompt()

# =========================
# MEMORY SYSTEM
# =========================

def load_memory():
    if not os.path.exists(MEMORY_FILE):
        return {}
    with open(MEMORY_FILE, "r") as f:
        return json.load(f)

def save_memory(memory):
    with open(MEMORY_FILE, "w") as f:
        json.dump(memory, f, indent=2)

def update_user_memory(user_id, user_input):
    memory = load_memory()

    if user_id not in memory:
        memory[user_id] = {
            "history": [],
            "patterns": []
        }

    memory[user_id]["history"].append({
        "input": user_input,
        "time": str(datetime.now())
    })

    # Simple pattern detection (expand later)
    if "confused" in user_input.lower():
        memory[user_id]["patterns"].append("confusion")

    save_memory(memory)
    return memory[user_id]

# =========================
# MODE DETECTION
# =========================

def detect_mode(user_input, user_memory):
    text = user_input.lower()

    # Analysis triggers
    if any(word in text for word in [
        "situation", "problem", "issue", "colleague", "boss",
        "relationship", "confused", "don't know", "what should"
    ]):
        if len(text.split()) > 15:
            return "analysis"

    # Pressure triggers (repeated patterns)
    if "patterns" in user_memory:
        if user_memory["patterns"].count("confusion") > 2:
            return "pressure"

    # Clarity triggers
    if any(word in text for word in ["confused", "overthinking"]):
        return "clarity"

    return "tactical"

# =========================
# BUILD MESSAGES
# =========================

def build_messages(user_input, user_memory, mode):
    memory_context = ""

    if user_memory and "history" in user_memory:
        recent = user_memory["history"][-3:]
        memory_context = "\n".join([f"- {h['input']}" for h in recent])

    system_message = SYSTEM_PROMPT + f"""

CURRENT MODE: {mode.upper()}

USER CONTEXT:
{memory_context}
"""

    return [
        {"role": "system", "content": system_message},
        {"role": "user", "content": user_input}
    ]

# =========================
# OPENROUTER CALL
# =========================

def call_model(messages):
    url = "https://openrouter.ai/api/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": MODEL,
        "messages": messages,
        "temperature": 0.7
    }

    response = requests.post(url, headers=headers, json=payload)
    data = response.json()

    try:
        return data["choices"][0]["message"]["content"]
    except:
        return "Error: Unable to generate response."

# =========================
# MAIN PIPELINE
# =========================

def process_input(user_id, user_input):
    # Update memory
    user_memory = update_user_memory(user_id, user_input)

    # Detect mode
    mode = detect_mode(user_input, user_memory)

    # Build messages
    messages = build_messages(user_input, user_memory, mode)

    # Get response
    response = call_model(messages)

    return response

# =========================
# TEST RUN
# =========================

if __name__ == "__main__":
    print("Dravon Umbra is live.\n")

    user_id = "test_user"

    while True:
        user_input = input("You: ")
        reply = process_input(user_id, user_input)
        print("\nDravon:\n")
        print(reply)
        print("\n" + "="*50 + "\n")