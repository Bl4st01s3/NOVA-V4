import queue
tts_queue = queue.Queue()

ai_text = ""
sentence_buffer = ""
tokens = [
    "Good ", "evening,", " sir", " or ", "madam.", " I ", "do ", "hope ", "this ", "day ", "has ", "been "
]

# We need to simulate the EXACT loop where the bug happens
for token in tokens:
    ai_text += token
    sentence_buffer += token

    # Notice this block!
    for punc in ['. ', '! ', '? ', '.\n', '!\n', '?\n']:
        if punc in sentence_buffer:
            parts = sentence_buffer.split(punc, 1)
            sentence_to_speak = parts[0] + punc.strip()
            if sentence_to_speak.strip():
                print(f"Queueing: '{sentence_to_speak.strip()}'")
                tts_queue.put(sentence_to_speak.strip())
            sentence_buffer = parts[1]
            # HERE is the problem: it breaks the punctuation loop, but what if there's MULTIPLE sentences
            # in the buffer? (e.g. LLM sends a massive chunk at once).
            # But the real issue from the logs: "Good evening, sir. It's an absolute pleasure..."
            # Wait, the logs show it DID queue "It's an absolute pleasure to be back online."
            # But it queued it AFTER the first sentence finished.
            # Why did it stop playing?
            break

print("Remaining buffer:", repr(sentence_buffer))
