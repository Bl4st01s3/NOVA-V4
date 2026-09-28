import pyttsx3
import pythoncom
import sounddevice as sd
import numpy as np
import scipy.io.wavfile as wav
import os
import threading
import queue

q = queue.Queue()
text = "Good evening, sir or madam. I do hope this day has been treating you well. I am NOVA, your personal systems operator and digital confidant, now fully online and ready to attend to your every need. The system is functioning within optimal parameters, and all necessary diagnostics indicate a healthy startup. Shall we begin?"
q.put(text)
q.put(None)

def apply_dsp_effects(audio_data, sample_rate, effect_type):
    audio_float = audio_data.astype(np.float32) / 32768.0
    import scipy.signal as signal
    if effect_type == "futuristic":
        delay_samples = int(sample_rate * 0.015)
        delayed_audio = np.zeros_like(audio_float)
        delayed_audio[delay_samples:] = audio_float[:-delay_samples]
        mixed = (audio_float * 0.7) + (delayed_audio * 0.3)
        ir_length = int(sample_rate * 0.3)
        t = np.linspace(0, 1, ir_length, endpoint=False)
        impulse = np.exp(-15 * t) * np.random.randn(ir_length)
        if len(mixed.shape) > 1:
            impulse = impulse[:, np.newaxis]
            reverb = signal.fftconvolve(mixed, impulse, mode='full', axes=0)[:len(mixed)]
        else:
            reverb = signal.fftconvolve(mixed, impulse, mode='full')[:len(mixed)]
        final_audio = (mixed * 0.8) + (reverb * 0.1)
    else:
        final_audio = audio_float
    final_audio = np.clip(final_audio, -1.0, 1.0)
    return (final_audio * 32767).astype(np.int16)


def tts_worker():
    pythoncom.CoInitialize()
    tts_engine = pyttsx3.init()

    while True:
        task = q.get()
        if task is None:
            break

        temp_file = "test_speech_2.wav"
        print(f"Saving to {temp_file}...")
        tts_engine.save_to_file(task, temp_file)
        tts_engine.runAndWait()
        print(f"Saved! Size: {os.path.getsize(temp_file)}")

        sample_rate, audio_data = wav.read(temp_file)
        print(f"Read WAV. SR: {sample_rate}, Shape: {audio_data.shape}")

        processed = apply_dsp_effects(audio_data, sample_rate, "futuristic")
        print(f"Processed shape: {processed.shape}")

        print("Playing via sounddevice...")
        sd.play(processed, sample_rate)
        sd.wait()
        print("Playback finished.")

t = threading.Thread(target=tts_worker)
t.start()
t.join()
