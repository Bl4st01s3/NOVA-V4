import json

conversation_history = [
    {"role": "assistant", "content": '{"name": "get_last_print", "parameters": {"printer_name": "system"}}'}
]

for msg in conversation_history:
    if msg["role"] == "assistant":
        try:
            data = json.loads(msg["content"])
            if "name" in data and "parameters" in data:
                # It hallucinated a tool call as text.
                print("Found hallucinated tool call.")
        except Exception:
            pass
