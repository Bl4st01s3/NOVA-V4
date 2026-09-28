import re

def strip_markdown(text):
    # Remove markdown code blocks
    text = re.sub(r'```[a-zA-Z]*\n', '', text)
    text = re.sub(r'```', '', text)
    # Replace underscores with spaces so the TTS engine doesn't explicitly say "underscore"
    text = text.replace('_', ' ')
    # Remove raw json brackets
    text = text.replace('{', '')
    text = text.replace('}', '')
    text = text.replace('"', '')
    return text

print(strip_markdown("The system is running JSON:\n```json\n{\n  \"status\": \"nominal_underscore\"\n}\n```"))
