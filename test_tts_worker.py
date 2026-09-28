import sys
import os
import queue
import sounddevice as sd
import numpy as np
import scipy.io.wavfile as wav

# Stub out Eel
class DummyEel:
    def expose(self, f): return f
sys.modules['eel'] = DummyEel()

import main

# Wait for worker thread to init
import time
time.sleep(1)

with open('dummy_text.txt', 'r') as f:
    text = f.read().strip()

# Send text
print("Sending text to worker...")
main.tts_queue.put(text)

# Wait a bit for it to finish
time.sleep(10)
print("Test complete.")
