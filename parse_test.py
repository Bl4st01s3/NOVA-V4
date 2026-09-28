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

    if any(punc in sentence_buffer for punc in ['. ', '! ', '? ', '.\n', '!\n', '?\n']):
        print(f"MATCH: {repr(sentence_buffer)}")
        tts_queue.put(sentence_buffer.strip())
        sentence_buffer = ""

while not tts_queue.empty():
    print(tts_queue.get())
