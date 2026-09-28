import openai
from unittest.mock import MagicMock

# The user is hitting: The model produced output that does not match the expected peg-native format
# This usually happens in LM Studio / llama.cpp when a specific tool parameter format is used and it tries
# to parse the grammar, OR when `tool_choice="none"` is passed and the server's OpenAI shim doesn't map it correctly.
# Wait, "peg-native format" implies grammar parsing failed.
# When tool_choice="none" is passed to LM Studio, it might be trying to load a blank grammar or failing.
