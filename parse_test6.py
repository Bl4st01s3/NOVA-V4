import queue
tts_queue = queue.Queue()

ai_text = ""
sentence_buffer = ""
tokens = [
    "Good ", "evening,", " sir", " or ", "madam.", " I ", "do ", "hope ", "this ", "day ", "has ", "been "
]

# Wait, if we use a while loop to pull ALL punctuations out of the current chunk!
# Because what if a chunk contains multiple sentences: "Hello. I am here. "
tokens2 = ["Hello. I am here. "]

for token in tokens2:
    ai_text += token
    sentence_buffer += token

    # Process ALL sentences currently fully formed in the buffer
    while True:
        matched_punc = None
        # Find the earliest punctuation mark in the buffer
        earliest_idx = len(sentence_buffer)

        for punc in ['. ', '! ', '? ', '.\n', '!\n', '?\n']:
            idx = sentence_buffer.find(punc)
            if idx != -1 and idx < earliest_idx:
                earliest_idx = idx
                matched_punc = punc

        if matched_punc:
            parts = sentence_buffer.split(matched_punc, 1)
            sentence_to_speak = parts[0] + matched_punc.strip()
            if sentence_to_speak.strip():
                print(f"Queueing: '{sentence_to_speak.strip()}'")
                tts_queue.put(sentence_to_speak.strip())
            sentence_buffer = parts[1]
        else:
            # No complete sentences left in the buffer
            break

print("Remaining buffer:", repr(sentence_buffer))
