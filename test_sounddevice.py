import sounddevice as sd
import numpy as np

# Generate a 1-second sine wave at 440 Hz
fs = 44100
t = np.linspace(0, 1, fs, False)
audio_data = 0.5 * np.sin(2 * np.pi * 440 * t)

print("Playing sine wave...")
sd.play(audio_data, fs)
sd.wait()
print("Done.")
