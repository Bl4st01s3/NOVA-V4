import numpy as np
import scipy.io.wavfile as wav
import scipy.signal as signal

def apply_dsp_effects(audio_data, sample_rate, effect_type):
    if effect_type == "natural":
        return audio_data

    audio_float = audio_data.astype(np.float32) / 32768.0

    if effect_type == "futuristic":
        delay_samples = int(sample_rate * 0.015)
        delayed_audio = np.zeros_like(audio_float)

        # NOTE: if audio is 2D (stereo), this will fail! Let's print the shape.
        print("audio_float shape:", audio_float.shape)
        if len(audio_float.shape) > 1:
            print("audio is stereo! We need to handle this.")

        delayed_audio[delay_samples:] = audio_float[:-delay_samples]

        mixed = (audio_float * 0.7) + (delayed_audio * 0.3)

        ir_length = int(sample_rate * 0.3)
        t = np.linspace(0, 1, ir_length, endpoint=False)
        impulse = np.exp(-15 * t) * np.random.randn(ir_length)

        # NOTE: if mixed is 2D and impulse is 1D, fftconvolve might behave unexpectedly depending on axes
        if len(mixed.shape) > 1:
            print("mixed is stereo, impulse is 1D")
            # need impulse to be 2D as well, or convolve per channel
            impulse = impulse[:, np.newaxis]

        reverb = signal.fftconvolve(mixed, impulse, mode='full', axes=0)[:len(mixed)]

        final_audio = (mixed * 0.8) + (reverb * 0.1)

    elif effect_type == "robotic":
        mixed = np.where(np.abs(audio_float) < 0.05, 0, audio_float)
        mixed = np.clip(mixed * 1.5, -1.0, 1.0)
        final_audio = mixed
    else:
        final_audio = audio_float

    final_audio = np.clip(final_audio, -1.0, 1.0)
    return (final_audio * 32767).astype(np.int16)

fs = 44100
t = np.linspace(0, 1, fs, False)
audio_mono = np.sin(2 * np.pi * 440 * t) * 32767
audio_stereo = np.column_stack((audio_mono, audio_mono)).astype(np.int16)

wav.write("dummy_stereo.wav", fs, audio_stereo)
sample_rate, audio_data = wav.read("dummy_stereo.wav")
print("Reading dummy_stereo.wav, shape:", audio_data.shape)

try:
    out = apply_dsp_effects(audio_data, sample_rate, "futuristic")
    print("Success. Processed shape:", out.shape)
except Exception as e:
    print("FAILED:", e)
