import pyttsx3
import queue
import time
import os

q = queue.Queue()
q.put("This is the first sentence.")
q.put("This is the second sentence.")
q.put("This is the third sentence.")
q.put(None)

def tts_worker():
    engine = pyttsx3.init()
    while True:
        text = q.get()
        if text is None:
            break
        print(f"Generating: {text}")
        temp_file = "test_speech.wav"
        engine.save_to_file(text, temp_file)
        engine.runAndWait()
        print(f"Generated. File exists: {os.path.exists(temp_file)}")
        if os.path.exists(temp_file):
            os.remove(temp_file)

tts_worker()
