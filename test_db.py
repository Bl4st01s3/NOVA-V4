import numpy as np
import main

# Test low volume (should be near 0%)
raw_quiet = np.random.normal(0, 0.001, 1024).astype(np.float32)
main.audio_callback(raw_quiet, 1024, None, None)
print(f"Quiet Speech: {main.get_current_volume()}%")

# Test loud volume (should be much higher)
raw_loud = np.random.normal(0, 0.1, 1024).astype(np.float32)
main.audio_callback(raw_loud, 1024, None, None)
print(f"Loud Speech: {main.get_current_volume()}%")

# Test fall-off smoothing (pass silence)
raw_silence = np.zeros(1024, dtype=np.float32)
main.audio_callback(raw_silence, 1024, None, None)
print(f"Silence Drop 1: {main.get_current_volume()}%")
main.audio_callback(raw_silence, 1024, None, None)
print(f"Silence Drop 2: {main.get_current_volume()}%")
