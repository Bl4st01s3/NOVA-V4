# The user's exact error from LM Studio:
# "The model produced output that does not match the expected peg-native format"
# This happens DURING the API stream generation when it violates the grammar!
# It happened exactly on the recurse!
# It was outputting `{"name": "get_last_print", ...}` and halfway through, LM Studio killed the stream and threw a 500 error!
# Why did it violate the grammar?
# Because `tool_choice="none"` tells the OpenAI shim to enforce a grammar that FORBIDS JSON or tool shapes.
# But the LLM (which is just weights) still tried to output JSON. The grammar parser caught it and crashed the request!
# Therefore, using `tool_choice="none"` with LM Studio + Llama 3.1 is bugged if the model decides to write JSON.
# Instead of `tool_choice="none"`, we should use `tool_choice="auto"` ALWAYS, but instruct it in a system prompt NOT to use tools for the recurse!
# Wait, if we use `tool_choice="auto"`, it will just natively output a real tool_call object again, which is perfectly fine!
# If it outputs a tool_call on the recurse, our loop doesn't handle a second recursion. It just logs it.
