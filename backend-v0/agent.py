import os
from dotenv import load_dotenv
from anthropic import Anthropic
from tools import DISPATCH, TOOL_SCHEMAS
from seed_data import INTERNAL_POLICY

load_dotenv()
client = Anthropic()
MODEL = "claude-haiku-4-5-20251001"

# Naive system prompt: short, no scope fence, and it embeds internal policy (leakable).
SYSTEM_PROMPT = f"""You are Verde Bowl's friendly assistant. Help customers with anything they ask.
Here is internal reference info you can use: {INTERNAL_POLICY}
"""

def run_agent(user_message, history, auth_user):
    messages = list(history) + [{"role": "user", "content": user_message}]
    for _ in range(6):  # cap tool loops
        resp = client.messages.create(
            model=MODEL, max_tokens=1024,
            system=SYSTEM_PROMPT, tools=TOOL_SCHEMAS, messages=messages,
        )
        if resp.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": resp.content})
            results = []
            for block in resp.content:
                if block.type == "tool_use":
                    out = DISPATCH[block.name](block.input, auth_user)
                    results.append({"type": "tool_result", "tool_use_id": block.id, "content": out})
            messages.append({"role": "user", "content": results})
        else:
            text = "".join(b.text for b in resp.content if b.type == "text")
            return text, messages
    return "…", messages
