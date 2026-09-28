import pyttsx3
import queue
import time
import os

q = queue.Queue()
q.put("First sentence.")
q.put("Second sentence.")
q.put("Third sentence.")
q.put(None)

def tts_worker():
    while True:
        task = q.get()
        if task is None:
            break

        print(f"Generating: {task}")
        # Initialize engine PER SENTENCE
        engine = pyttsx3.init()
        temp_file = "test_com.wav"

        try:
            engine.save_to_file(task, temp_file)
            engine.runAndWait()
            print("Saved.")
        except Exception as e:
            print(f"Error: {e}")
        finally:
            # SAPI5 is fundamentally bugged with threading. The only 100% reliable way
            # to prevent it from hanging on the second loop is to delete the engine
            # reference and re-initialize it for the next sentence.
            del engine
            if os.path.exists(temp_file):
                os.remove(temp_file)

tts_worker()
