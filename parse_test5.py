import queue
tts_queue = queue.Queue()

ai_text = ""
sentence_buffer = ""
tokens = [
    "Good ", "evening,", " sir.\n\n", "The ", "system ", "is ", "running ", "JSON:\n", "```json\n", "{\n  \"status\": ", "\"nominal_underscore\"\n", "}\n```"
]

for token in tokens:
    ai_text += token
    sentence_buffer += token

    # We want to catch the punctuation and split immediately so we don't accidentally send the next word too
    for punc in ['. ', '! ', '? ', '.\n', '!\n', '?\n']:
        if punc in sentence_buffer:
            parts = sentence_buffer.split(punc, 1)
            # The actual sentence is the first part + the punctuation
            sentence_to_speak = parts[0] + punc.strip()
            if sentence_to_speak.strip():
                print(f"MATCH: {repr(sentence_to_speak)}")
                tts_queue.put(sentence_to_speak.strip())

            # Keep whatever came after the punctuation in the buffer
            sentence_buffer = parts[1]
            break

if sentence_buffer.strip():
    print(f"FINAL BUFFER: {repr(sentence_buffer)}")
    tts_queue.put(sentence_buffer.strip())

while not tts_queue.empty():
    print("IN QUEUE:", repr(tts_queue.get()))
