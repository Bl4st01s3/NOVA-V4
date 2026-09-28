import re

text = """{"name": "get_last_print", "parameters": {"printer_name": "system"}}"""
def clean_text_for_speech(text):
    text = text.replace('_', ' ')
    text = text.replace('{', '')
    text = text.replace('}', '')
    text = text.replace('"', '')
    text = re.sub(r'```[a-zA-Z]*\n', '', text)
    text = re.sub(r'```', '', text)
    return text.strip()

print(clean_text_for_speech(text))
