# Wait, look at the error log from user:
# 2026-09-28 23:11:42,930 - INFO - HTTP Request: POST http://localhost:1234/v1/chat/completions "HTTP/1.1 200 OK"
# This is the initial LLM call...
# Then it called octoprint.
# Then: `2026-09-28 23:11:43,546 - ERROR - Error: Unable to reach the Bionic Engine. Please check that LM Studio is running and responding. Details: Engine protocol predict stream returned an error: {"code":500,"message":"The model produced output that does not match the expected peg-native format","type":"server_error"}`
# This error happened DURING the recurse stream!
# Because during the recurse, we use kwargs2 with `tool_choice="none"`.
# When we passed `tool_choice="none"`, LM Studio constructed a grammar that physically PREVENTED the model from writing `{`.
# But because the model weights decided "I want to output JSON now because the history has a tool call", it output `{`.
# The parser crashed!

# We CANNOT pass `tool_choice="none"` to LM Studio. It causes the grammar parser to crash.
# We must pass `tool_choice="auto"` ALWAYS, but inject a strong system prompt instruction to the end of the history array telling it not to use tools.
# Let's fix this in both places:
# 1. Boot sequence
# 2. Recurse sequence
# 3. Presence sequence
