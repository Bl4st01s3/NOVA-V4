import openai
# The bug: LM studio throws 'The model produced output that does not match the expected peg-native format'
# when tool_choice="none" is used with a model that natively supports function calling grammar, or
# when the model generates raw JSON (like {"printer_name": "system"}) OUTSIDE of the actual tool_call object block!
# Yes! Look at the logs:
# `NOVA: {"name": "get_last_print", "parameters": {"printer_name": "system"}}`
# It output raw JSON as the message content, not as a tool call!
# And then LM Studio crashed because the content was formatted like a tool call but violated the grammatical rules.
# Wait, LM Studio crashed on the RECURSE call.
# "LLM called tool 'octoprint' with args..."
# "Tool result: Octoprint Status: Voron 2.4 finished..."
# THEN it outputs `NOVA: {"name": "get_last_print", "parameters": {"printer_name": "system"}}`
# Then LM Studio crashes on the next call.
