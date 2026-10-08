import os
import urllib.request
import json

MODELS_DIR = "piper_models"

# A curated list of 6 Piper voices (prioritizing UK Female)
VOICES = {
    "en_GB-alba-medium": {
        "name": "Alba (UK Female, Medium)",
        "desc": "A clear, natural British female voice.",
        "onnx": "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_GB/alba/medium/en_GB-alba-medium.onnx",
        "json": "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_GB/alba/medium/en_GB-alba-medium.onnx.json"
    },
    "en_GB-jenny_dioco-medium": {
        "name": "Jenny (UK Female, Medium)",
        "desc": "A bright, articulate British female voice.",
        "onnx": "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_GB/jenny_dioco/medium/en_GB-jenny_dioco-medium.onnx",
        "json": "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_GB/jenny_dioco/medium/en_GB-jenny_dioco-medium.onnx.json"
    },
    "en_GB-semaine-medium": {
        "name": "Semaine (UK Female, Medium)",
        "desc": "A steady, professional British female voice.",
        "onnx": "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_GB/semaine/medium/en_GB-semaine-medium.onnx",
        "json": "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_GB/semaine/medium/en_GB-semaine-medium.onnx.json"
    },
    "en_GB-northern_english_male-medium": {
        "name": "Northern (UK Male, Medium)",
        "desc": "A deep, authoritative Northern British male voice.",
        "onnx": "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_GB/northern_english_male/medium/en_GB-northern_english_male-medium.onnx",
        "json": "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_GB/northern_english_male/medium/en_GB-northern_english_male-medium.onnx.json"
    },
    "en_GB-cori-high": {
        "name": "Cori (UK Male, High)",
        "desc": "A refined, Jarvis-like British male voice.",
        "onnx": "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_GB/cori/high/en_GB-cori-high.onnx",
        "json": "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_GB/cori/high/en_GB-cori-high.onnx.json"
    },
    "en_US-libritts-high": {
        "name": "LibriTTS (US Female, High)",
        "desc": "A highly trained, natural American female voice.",
        "onnx": "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/libritts/high/en_US-libritts-high.onnx",
        "json": "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/libritts/high/en_US-libritts-high.onnx.json"
    }
}

def download_voice(voice_id):
    if voice_id not in VOICES:
        print(f"Error: Voice ID {voice_id} not found.")
        return False

    os.makedirs(MODELS_DIR, exist_ok=True)
    voice_data = VOICES[voice_id]

    onnx_path = os.path.join(MODELS_DIR, f"{voice_id}.onnx")
    json_path = os.path.join(MODELS_DIR, f"{voice_id}.onnx.json")

    if os.path.exists(onnx_path) and os.path.exists(json_path):
        print(f"Voice {voice_id} is already downloaded.")
        return True

    print(f"Downloading {voice_id} (.onnx)...")
    try:
        urllib.request.urlretrieve(voice_data["onnx"], onnx_path)
    except Exception as e:
        print(f"Failed to download .onnx: {e}")
        return False

    print(f"Downloading {voice_id} (.json)...")
    try:
        urllib.request.urlretrieve(voice_data["json"], json_path)
    except Exception as e:
        print(f"Failed to download .json: {e}")
        return False

    print(f"Successfully downloaded {voice_id}.")
    return True

if __name__ == "__main__":
    print("Setting up default Piper TTS models...")
    download_voice("en_GB-alba-medium")