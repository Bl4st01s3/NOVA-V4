import queue
tts_queue = queue.Queue()

ai_text = ""
sentence_buffer = ""
tokens = [
    "Good ", "evening,", " sir", " or ", "madam.", " I ", "do ", "hope ", "this ", "day ", "has ", "been "
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
            print(f"MATCH: {repr(sentence_to_speak)}")
            tts_queue.put(sentence_to_speak.strip())

            # Keep whatever came after the punctuation in the buffer
            sentence_buffer = parts[1]
            break

while not tts_queue.empty():
    print("IN QUEUE:", repr(tts_queue.get()))
