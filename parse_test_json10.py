# The user's bug: LM studio crashes with peg-native format error when tool_choice="none" is used with LM Studio.
# This confirms that passing `tool_choice="none"` to LM Studio violates their internal parser when used with Llama 3.1 GBNF grammar.
# Wait, look closely at the crash:
# "The model produced output that does not match the expected peg-native format"
# This means the MODEL produced it, NOT that the API rejected the parameter.
# Meaning LM Studio *did* accept `tool_choice="none"`. It applied a strict grammar constraint that forces the model to ONLY output normal text.
# But because the conversation history contained the previous tool calls (which we injected back into the messages array),
# the LLM thought it was STILL supposed to output JSON, so it generated `{"name": "get_last_print"...}`.
# The grammar parser caught the `{` and immediately terminated the stream because `{` is illegal when tool_choice="none"!
# Ah!! This is a brilliant catch!

# We need to PREVENT the LLM from outputting JSON when it shouldn't.
# If we simply don't pass tools at all during the recurse, the cache busts.
# If we use tool_choice="auto", it will infinitely loop calling tools if it's hallucinating.
# What if we just append a system prompt instruction to the end of the history array before recursing?
# Like: {"role": "system", "content": "You have received the tool data. Now output the final response in plain spoken text to the user. DO NOT use tools or JSON."}
# Let's try that, but keeping `tool_choice="auto"` so the grammar doesn't crash if it slips up.
