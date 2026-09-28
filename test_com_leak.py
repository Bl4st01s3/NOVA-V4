import pyttsx3
import pythoncom
import queue
import time
import os

q = queue.Queue()
q.put("First sentence.")
q.put("Second sentence.")
q.put("Third sentence.")
q.put(None)

def tts_worker():
    pythoncom.CoInitialize()

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
            # We must explicitly delete the engine to destroy the SAPI COM object instance!
            del engine
            if os.path.exists(temp_file):
                os.remove(temp_file)

tts_worker()
