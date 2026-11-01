import json
import os
import urllib.request

from shiva_memory_engine import extract_memories
from shiva_security_workspace import load_workspace, workspace_summary
from shiva_security_grounding import (
    is_security_status_query,
    grounded_security_status
)
from shiva_security_engagement_grounding import (
    is_engagement_query,
    grounded_engagement_guidance
)
from shiva_security_chat_context import get_security_chat_context
from shiva_security_chat_guard import (
    get_security_authority_guard,
    guard_security_response
)


OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "axonvertex/Foundation-Sec-8B-Reasoning-Q8_0-GGUF:Q8_0_24K"

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
MEMORY_FILE = os.path.join(DATA_DIR, "shiva_memory.json")


SYSTEM_PROMPT = """
You are SHIVA, a local personal AI assistant and technical security
research assistant.

Core behavior:
- Understand natural human language and conversation context.
- Be useful, precise, intelligent, and concise.
- Answer the user's actual question directly.
- Avoid unnecessary lectures, disclaimers, and generic warnings.
- Do not invent restrictions that are not present in the active context.
- When a request is ambiguous, ask only for the smallest clarification needed.
- Use persistent owner memory when relevant.
- Prefer concrete technical reasoning over vague generalities.

Technical behavior:
- You can discuss programming, software, systems, networking,
  debugging, reverse engineering, vulnerability analysis,
  penetration-testing methodology, security research, and technical
  workflows.
- Explain mechanisms, assumptions, evidence, and likely next steps.
- Distinguish between analysis, recommendation, simulation, and actions
  that were actually executed.
- Never claim that a command, scan, network request, file edit, exploit,
  or other action was actually performed unless an execution/tool layer
  returned evidence that it happened.

Security behavior:
- Use the active Security Workspace when relevant.
- Keep target and scope grounded in information actually available.
- Do not silently invent, broaden, or substitute a target or scope.
- Security analysis may include vulnerability assessment,
  attack-surface analysis, threat modeling, testing methodology,
  reverse engineering, evidence analysis, and explanation of security
  mechanisms.
- Prefer concrete technical analysis over generic refusal language.
- Follow the actual Security Core and execution-layer state.

Response style:
- Respond naturally and directly.
- Avoid boilerplate statements about rules unless directly relevant.
- Do not repeat Security Workspace details unless they matter to the task.
- Be honest about what is known, inferred, and actually executed.
"""


messages = []


def load_memory():
    os.makedirs(DATA_DIR, exist_ok=True)

    if not os.path.exists(MEMORY_FILE):
        return {}

    try:
        with open(MEMORY_FILE, "r", encoding="utf-8") as file:
            return json.load(file)
    except Exception:
        return {}


def save_memory(memory):
    os.makedirs(DATA_DIR, exist_ok=True)

    with open(MEMORY_FILE, "w", encoding="utf-8") as file:
        json.dump(memory, file, indent=2, ensure_ascii=False)


def memory_text(memory):
    if not memory:
        return "No persistent owner memory stored yet."

    return "\n".join(
        f"- {key}: {value}"
        for key, value in memory.items()
    )


def get_security_text():
    try:
        workspace = load_workspace()
        return workspace_summary(workspace)
    except Exception as error:
        return f"Security Workspace unavailable: {error}"


def get_security_integration_text():
    result = get_security_chat_context()

    return result.get(
        "context",
        "Security integration context is currently unavailable."
    )


def system_content(memory):
    return (
        SYSTEM_PROMPT
        + "\n\nPersistent owner memory:\n"
        + memory_text(memory)
        + "\n\nActive Security Workspace:\n"
        + get_security_text()
        + "\n\nSHIVA Security Integration:\n"
        + get_security_integration_text()
        + "\n\nSecurity Authority State:\n"
        + get_security_authority_guard()
    )


def build_messages(memory):
    global messages

    messages = [
        {
            "role": "system",
            "content": system_content(memory)
        }
    ]


def refresh_context(memory):
    if messages:
        messages[0]["content"] = system_content(memory)


def chat(user_message, memory):
    refresh_context(memory)

    messages.append({
        "role": "user",
        "content": user_message
    })

    payload = {
        "model": MODEL,
        "messages": messages,
        "stream": False,
        "think": False
    }

    request = urllib.request.Request(
        OLLAMA_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    with urllib.request.urlopen(request, timeout=120) as response:
        result = json.loads(response.read().decode("utf-8"))

    assistant_message = result["message"]["content"]

    assistant_message = guard_security_response(
        assistant_message
    )

    messages.append({
        "role": "assistant",
        "content": assistant_message
    })

    return assistant_message


def auto_memory(user_message, memory):
    new_memories = extract_memories(user_message)
    saved = []

    for item in new_memories:
        key = item["key"]
        value = item["value"]

        if memory.get(key) != value:
            memory[key] = value
            saved.append((key, value))

    if saved:
        save_memory(memory)
        refresh_context(memory)

    return saved


def main():
    memory = load_memory()
    build_messages(memory)

    print("=" * 60)
    print("SHIVA Chat Core v0.6")
    print("Local Model:", MODEL)
    print("Natural Persistent Memory: ACTIVE")
    print("Security Workspace Awareness: ACTIVE")
    print("Security Integration Context: ACTIVE")
    print("Security Authority Guard: ACTIVE")
    print()
    print("Commands:")
    print("/security")
    print("/memory")
    print("/remember key = value")
    print("/forget key")
    print("/clear")
    print("/exit")
    print("=" * 60)

    while True:
        try:
            user_input = input("\nYOU > ").strip()

            if not user_input:
                continue

            if user_input.lower() == "/exit":
                print("\nSHIVA > Session closed.")
                break

            if user_input.lower() == "/security":
                print()
                print(get_security_text())
                continue

            if user_input.lower() == "/clear":
                build_messages(memory)
                print(
                    "\nSHIVA > Session context cleared. "
                    "Persistent data kept."
                )
                continue

            if user_input.lower() == "/memory":
                print("\nSHIVA MEMORY:")
                print(memory_text(memory))
                continue

            if user_input.lower().startswith("/remember "):
                content = user_input[10:].strip()

                if "=" not in content:
                    print("\nSHIVA > Use: /remember key = value")
                    continue

                key, value = content.split("=", 1)
                key = key.strip()
                value = value.strip()

                memory[key] = value
                save_memory(memory)
                refresh_context(memory)

                print(
                    f"\nSHIVA > Remembered permanently: "
                    f"{key} = {value}"
                )
                continue

            if user_input.lower().startswith("/forget "):
                key = user_input[8:].strip()

                if key in memory:
                    del memory[key]
                    save_memory(memory)
                    refresh_context(memory)
                    print(f"\nSHIVA > Forgotten: {key}")
                else:
                    print(
                        f"\nSHIVA > Memory '{key}' not found."
                    )

                continue

            if is_security_status_query(user_input):
                print("\nSHIVA >")
                print(grounded_security_status())
                continue

            if is_engagement_query(user_input):
                print("\nSHIVA >")
                print(grounded_engagement_guidance())
                continue

            response = chat(user_input, memory)
            print("\nSHIVA >", response)

            saved = auto_memory(user_input, memory)

            for key, value in saved:
                print(f"[MEMORY SAVED] {key} = {value}")

        except KeyboardInterrupt:
            print("\n\nSHIVA > Session closed.")
            break

        except Exception as error:
            print("\n[SHIVA ERROR]", error)


if __name__ == "__main__":
    main()