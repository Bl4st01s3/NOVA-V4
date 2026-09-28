# The user's specific LM Studio error is:
# "The model produced output that does not match the expected peg-native format"
# This happens specifically when using llama.cpp server and passing `tool_choice="none"`.
# The llama.cpp server uses GBNF (Generalized Backus-Naur Form) grammars to enforce tool calling.
# When `tool_choice` is "none", it probably expects the model to output normal text, but the model
# might still try to output JSON format due to the system prompt injection, and the parser crashes,
# OR passing `tool_choice="none"` to LM Studio invokes a bug in their peg parser.
#
# If we omit tools, KV caching breaks because the system prompt changes.
# Instead of `tool_choice="none"`, we can just let it have `tool_choice="auto"` but instruct it NOT to use tools!
