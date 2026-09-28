# Ah!
# 1. User: how is your KV caching...
# 2. LLM responds with a tool call for Octoprint.
# 3. System handles tool call, appends tool result to history.
# 4. System RECURSES to LLM with tool_choice="none"
# 5. LLM generates {"name": "get_last_print", "parameters": {"printer_name": "system"}} AS CONTENT
# 6. System appends that content to conversation_history!
# 7. User sends another message.
# 8. LM Studio reads the history, sees {"name": "get_last_print", ...} in the history, and CRASHES
#    because LM Studio thinks it's a malformed tool call or violates the grammar!
#
# We need to strip or clean LLM content BEFORE appending it to history if it's raw JSON hallucination.
# Actually, if the LLM hallucinates raw JSON as content, LM Studio's strict `llama.cpp` parser might crash
# on the NEXT turn when it evaluates the history against the grammar.
# And why did it hallucinate a second tool call? Because tool_choice="none" means "don't generate a tool call block",
# but it still generated the JSON schema as normal text because it thought it was supposed to call another tool!
# If we pass `tool_choice="none"`, we should probably completely strip the tools array if we don't want it using tools on the recurse.
# But stripping tools busts the KV cache!
