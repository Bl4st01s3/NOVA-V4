import numpy as np
import scipy.io.wavfile as wav
import scipy.signal as signal

def apply_dsp_effects(audio_data, sample_rate, effect_type):
    """Applies numpy/scipy math to raw audio array to simulate J.A.R.V.I.S effects."""
    if effect_type == "natural":
        return audio_data

    # Convert to float for math
    audio_float = audio_data.astype(np.float32) / 32768.0

    if effect_type == "futuristic":
        # 1. Simple Chorus/Flanger (Double the track, pitch shift slightly and delay)
        delay_samples = int(sample_rate * 0.015) # 15ms delay
        delayed_audio = np.zeros_like(audio_float)
        delayed_audio[delay_samples:] = audio_float[:-delay_samples]

        # Mix dry and wet
        mixed = (audio_float * 0.7) + (delayed_audio * 0.3)

        # 2. Convolution Reverb (Simulate a metallic room)
        # Create an exponentially decaying impulse response
        ir_length = int(sample_rate * 0.3) # 300ms tail
        t = np.linspace(0, 1, ir_length, endpoint=False)
        impulse = np.exp(-15 * t) * np.random.randn(ir_length)

        # Convolve
        reverb = signal.fftconvolve(mixed, impulse, mode='full')[:len(mixed)]

        # Mix reverb back in lightly
        final_audio = (mixed * 0.8) + (reverb * 0.1)

    elif effect_type == "robotic":
        # Robotic: hard noise gate + slight distortion + tight reverb
        mixed = np.where(np.abs(audio_float) < 0.05, 0, audio_float) # Noise gate
        mixed = np.clip(mixed * 1.5, -1.0, 1.0) # Distort
        final_audio = mixed
    else:
        final_audio = audio_float

    # Normalize back to 16-bit PCM
    final_audio = np.clip(final_audio, -1.0, 1.0)
    return (final_audio * 32767).astype(np.int16)

fs = 44100
t = np.linspace(0, 1, fs, False)
audio_mono = np.sin(2 * np.pi * 440 * t) * 32767
audio_stereo = np.column_stack((audio_mono, audio_mono)).astype(np.int16)

wav.write("dummy_stereo2.wav", fs, audio_stereo)
sample_rate, audio_data = wav.read("dummy_stereo2.wav")

try:
    out = apply_dsp_effects(audio_data, sample_rate, "futuristic")
    print("Success. Processed shape:", out.shape)
except Exception as e:
    import traceback
    traceback.print_exc()
    print("FAILED:", e)
