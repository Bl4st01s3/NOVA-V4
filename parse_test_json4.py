# If tool_choice is none, some servers (especially OpenAI shims for local models like LM Studio)
# expect it to be passed differently, or not pass tools at all if it's "none".
# Wait, "peg-native format" from llama.cpp usually means grammar violation.
# If tools are passed, llama.cpp constructs a complex BNF grammar for tool calling.
# If tool_choice is "none", it might be trying to load a grammar that enforces NO tool calls,
# but the grammar generation fails.
# The simplest fix for "The model produced output that does not match the expected peg-native format"
# is to NOT PASS the tools array if we don't want it to use tools.
# The user claims KV caching is broken when tools aren't passed.
# BUT Llama.cpp prompt caching caches the system prompt. If the tools array is injected into the system prompt
# then yes, omitting tools changes the prompt prefix and breaks the cache.
# How does LM Studio inject tools? It appends them to the system prompt.
