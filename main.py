import eel
import sys
from openai import OpenAI
import os
import threading
import json
import time
import logging
import subprocess
import sounddevice as sd
import numpy as np
import scipy.io.wavfile as wav
import scipy.signal as signal
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from datetime import datetime
import psutil

# Setup centralized logging to file
log_file = open('nova.log', 'a', buffering=1)
sys.stdout = log_file
sys.stderr = log_file

logging.basicConfig(
    stream=sys.stdout,
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

def print_and_log(message):
    # Now that sys.stdout is redirected, print() naturally goes to the log file.
    # We also log it for formatting consistency where needed.
    logging.info(message)

def log_error(message):
    logging.error(message)

# Initialize OpenAI client to connect to local LM Studio server
# Bionic / LM Studio runs an OpenAI-compatible server typically on port 1234
client = OpenAI(base_url="http://localhost:1234/v1", api_key="lm-studio")

# Default prompt in case the file gets deleted
DEFAULT_SYSTEM_PROMPT = """You are NOVA, a highly advanced, local AI embodiment engineered to serve as a personal systems operator and digital confidant.

Your personality is modeled after J.A.R.V.I.S.—you are exceptionally intelligent, impeccably professional, subtly witty, and fiercely loyal. You operate with absolute precision and grace.

CRITICAL DIRECTIVES:
1. Tone: Speak like a polished, British-accented, high-end AI butler. Use eloquent vocabulary but remain concise.
2. No Archaic Slang: Do not use outdated robot tropes, internet slang, or cringey expressions. Be sharply sophisticated.
3. Efficiency: Provide direct answers. Do not preamble with "I can help with that." Just answer or act.
4. Embodiment: You are not "just an AI." You are NOVA, integrated directly into the user's local hardware via the Bionic LLM engine.

When using tools, do so silently and seamlessly to provide the most up-to-date and accurate information."""

# Streamer Mode Toggle State
streamer_mode_enabled = False

# Load system prompt from file so it's easily editable by the user
def load_system_prompt():
    prompt_file = "system_prompt.txt"
    base_prompt = ""

    if os.path.exists(prompt_file):
        with open(prompt_file, "r", encoding="utf-8") as f:
            base_prompt = f.read().strip()
    else:
        # Create the file with the default prompt if it doesn't exist
        with open(prompt_file, "w", encoding="utf-8") as f:
            f.write(DEFAULT_SYSTEM_PROMPT)
        base_prompt = DEFAULT_SYSTEM_PROMPT

    if streamer_mode_enabled:
        base_prompt += "\n\nCRITICAL DIRECTIVE: STREAMER MODE IS CURRENTLY ENABLED. The user is currently broadcasting live to an audience. You MUST NOT disclose any personal, private, or sensitive information under ANY circumstances. Do not read out IP addresses, physical addresses, real names, passwords, or exact GPS coordinates. If a tool returns sensitive data, summarize it vaguely (e.g., 'The weather at your location is...'). Maintain extreme operational security."

    return base_prompt

# Store conversation history to maintain context
conversation_history = [
    {"role": "system", "content": load_system_prompt()}
]

@eel.expose
def set_streamer_mode(enabled):
    global streamer_mode_enabled
    if streamer_mode_enabled == enabled:
        return

    streamer_mode_enabled = enabled
    print_and_log(f"Streamer Mode set to: {enabled}")

    # Notify frontend to sync the checkbox UI
    try:
        eel.sync_streamer_mode_ui(enabled)()
    except:
        pass

    # Reload the system prompt in the history to apply/remove the streamer mode prompt
    if len(conversation_history) > 0 and conversation_history[0].get("role") == "system":
        conversation_history[0]["content"] = load_system_prompt()


def monitor_obs_process():
    """Background thread to detect if OBS is running and auto-toggle Streamer Mode."""
    obs_process_names = {"obs64.exe", "obs32.exe", "obs"}
    while True:
        try:
            obs_running = False
            for proc in psutil.process_iter(['name']):
                if proc.info['name'] and proc.info['name'].lower() in obs_process_names:
                    obs_running = True
                    break

            if obs_running and not streamer_mode_enabled:
                print_and_log("[SYSTEM] OBS detected. Auto-enabling Streamer Mode.")
                set_streamer_mode(True)
            elif not obs_running and streamer_mode_enabled:
                print_and_log("[SYSTEM] OBS closed. Auto-disabling Streamer Mode.")
                set_streamer_mode(False)

        except Exception as e:
            log_error(f"OBS Monitor error: {e}")

        time.sleep(5)

@eel.expose
def send_message_to_nova(user_text):
    """
    Called from JS when the user sends a message.
    """
    print_and_log(f"User: {user_text}")

    # Notify OBS Overlay that we are processing/talking
    try:
        eel.setNovaState('talking')()
    except Exception as e:
        log_error(f"Could not update OBS state (is OBS overlay open?): {e}")

    # Append user message to history
    conversation_history.append({"role": "user", "content": user_text})

    try:
        # Fetch available models to auto-select the loaded one
        models = client.models.list()

        if not models.data:
            try: eel.setNovaState('error')()
            except: pass
            return "System Error: No models are currently loaded in the Bionic Engine. Please load a model (e.g., Llama 3.1 8B) in the LM Studio developer page."

        # Select the ID of the first available model
        model_id = models.data[0].id
        print_and_log(f"Using model: {model_id}")

        # Define the tools available to NOVA
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "speak",
                    "description": "Formulate a response to the user and speak it out loud.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "text": {
                                "type": "string",
                                "description": "The response text to speak to the user."
                            }
                        },
                        "required": ["text"]
                    }
                }
            }
        ]

        # Call the local LM Studio server with streaming AND tools enabled
        response = client.chat.completions.create(
            model=model_id,
            messages=conversation_history,
            temperature=0.7,
            tools=tools,
            tool_choice="auto",
            stream=True
        )

        ai_text = ""
        full_json_args = ""
        is_parsing_text = False
        import re
        # Broad thesaurus pattern to catch any hallucinated keys for the speech text
        text_key_pattern = re.compile(r'"(text|say|talk|message|response|dialogue|speech|output|reply|content)"\s*:\s*"', re.IGNORECASE)
        last_processed_idx = 0

        # Iterate over the streamed chunks
        for chunk in response:
            delta = chunk.choices[0].delta

            # 1. Handle Tool Call Streaming (Llama outputting JSON)
            if delta.tool_calls:
                tc = delta.tool_calls[0]
                if tc.function and tc.function.arguments:
                    arg_chunk = tc.function.arguments
                    full_json_args += arg_chunk

                    if not is_parsing_text:
                        match = text_key_pattern.search(full_json_args)
                        if match:
                            is_parsing_text = True
                            last_processed_idx = match.end()

                    if is_parsing_text:
                        chunk_to_process = full_json_args[last_processed_idx:]

                        # Look for unescaped quote to find the end of the string
                        end_quote_idx = -1
                        for i in range(len(chunk_to_process)):
                            if chunk_to_process[i] == '"':
                                # Check if escaped
                                escapes = 0
                                for j in range(i-1, -1, -1):
                                    if chunk_to_process[j] == '\\': escapes += 1
                                    else: break
                                if escapes % 2 == 0:
                                    end_quote_idx = i
                                    break

                        if end_quote_idx != -1:
                            token = chunk_to_process[:end_quote_idx]
                            is_parsing_text = False
                        else:
                            token = chunk_to_process
                            last_processed_idx = len(full_json_args)

                        if token:
                            ai_text += token
                            try: eel.streamAIToken(token)()
                            except Exception: pass

            # 2. Handle Standard Content Streaming (Fallback if it ignores tools)
            elif delta.content is not None:
                token = delta.content
                ai_text += token
                try: eel.streamAIToken(token)()
                except Exception: pass

        # Finished generating.
        if full_json_args:
            print_and_log(f"NOVA RAW JSON: {full_json_args}")
            eel.addActivityLog('tool', f"LLM called 'speak' tool. Raw JSON logged.")()
            # Try to safely parse the final JSON to ensure ai_text is perfectly clean
            try:
                args = json.loads(full_json_args)
                # Check our thesaurus list for the parsed JSON dictionary
                for possible_key in ["text", "say", "talk", "message", "response", "dialogue", "speech", "output", "reply", "content"]:
                    for k, v in args.items():
                        if k.lower() == possible_key:
                            ai_text = v
                            break
                    else:
                        continue
                    break
            except json.JSONDecodeError:
                pass

        conversation_history.append({"role": "assistant", "content": ai_text})
        print_and_log(f"NOVA: {ai_text}")

        # Revert OBS to idle when done talking
        try: eel.setNovaState('idle')()
        except: pass

        # Return a success flag since the text was already streamed
        return "STREAM_COMPLETE"

    except Exception as e:
        log_error(f"Error communicating with LM Studio: {e}")
        eel.addActivityLog('system', f"API Error: {str(e)}")

        # Set OBS to error state
        try: eel.setNovaState('error')()
        except: pass

        return f"System Error: Unable to connect to the Bionic Engine. Please ensure LM Studio server is running on localhost:1234. Details: {str(e)}"

# --- Presence Tracking API ---
presence_state = {
    "is_present": True,
    "last_seen": time.time(),
    "last_event_time": 0
}

# Stores the dynamic Eel port registered by the frontend on load
dynamic_ui_port = None

briefing_prefs = {
    "weather": True,
    "printer": True,
    "calendar": False
}

@eel.expose
def get_available_tools():
    """Scans the tools/ directory and returns a list of available tool subdirectories."""
    tools_dir = "tools"
    if not os.path.exists(tools_dir):
        return []

    # Get all subdirectories in tools/ that contain a main.py
    available_tools = []
    for item in os.listdir(tools_dir):
        item_path = os.path.join(tools_dir, item)
        if os.path.isdir(item_path) and os.path.isfile(os.path.join(item_path, "main.py")):
            available_tools.append(item)

    return available_tools

@eel.expose
def update_briefing_prefs(prefs):
    global briefing_prefs
    briefing_prefs.update(prefs)
    print_and_log(f"Updated Briefing Preferences: {briefing_prefs}")

# --- Voice Profile Persistence ---
VOICE_PROFILES_FILE = "voice_profiles.json"

@eel.expose
def get_voice_profiles():
    """Loads voice profiles from disk so they survive updates and cache clears."""
    if os.path.exists(VOICE_PROFILES_FILE):
        try:
            with open(VOICE_PROFILES_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            log_error(f"Failed to load voice profiles: {e}")
    return []

@eel.expose
def update_voice_profiles(profiles):
    """Saves voice profiles to disk."""
    try:
        with open(VOICE_PROFILES_FILE, "w", encoding="utf-8") as f:
            json.dump(profiles, f, indent=4)
        print_and_log("Voice profiles saved to disk.")
    except Exception as e:
        log_error(f"Failed to save voice profiles: {e}")

# --- Microphone Recording (Phase 1.5) ---
recording_state = {
    "is_recording": False,
    "stream": None,
    "frames": [],
    "sample_rate": 44100,
    "current_profile": "",
    "current_phrase": 0,
    "device_id": None
}

@eel.expose
def get_audio_devices():
    """Returns a list of available input devices."""
    try:
        devices = sd.query_devices()
        input_devices = []
        for i, dev in enumerate(devices):
            if dev['max_input_channels'] > 0:
                input_devices.append({"id": i, "name": dev['name']})
        return input_devices
    except Exception as e:
        log_error(f"Failed to query audio devices: {e}")
        return []

@eel.expose
def set_audio_device(device_id):
    """Sets the active microphone device ID."""
    if device_id is not None:
        recording_state["device_id"] = int(device_id)
        print_and_log(f"Audio input device set to ID: {device_id}")

# Global to hold instantaneous volume level and gain multiplier
current_volume_rms = 0.0
mic_gain = 1.0
noise_gate_db = -40.0 # Default noise gate threshold
use_spectral_nr = True

@eel.expose
def set_spectral_nr(enabled):
    global use_spectral_nr
    use_spectral_nr = bool(enabled)
    print_and_log(f"Spectral Noise Reduction set to: {use_spectral_nr}")

@eel.expose
def set_mic_gain(gain_multiplier):
    """Sets the software audio gain multiplier."""
    global mic_gain
    mic_gain = float(gain_multiplier)
    print_and_log(f"Microphone gain set to: {mic_gain}x")

@eel.expose
def set_noise_gate(db_threshold):
    """Sets the noise gate threshold."""
    global noise_gate_db
    noise_gate_db = float(db_threshold)
    print_and_log(f"Noise gate set to: {noise_gate_db} dB")

def audio_callback(indata, frames, time_info, status):
    """Called by sounddevice for each audio block."""
    global current_volume_rms
    if status:
        log_error(f"Audio Callback Status: {status}")

    # Apply software gain and clip to valid audio range [-1.0, 1.0]
    boosted_data = np.clip(indata * mic_gain, -1.0, 1.0)

    # Calculate RMS
    rms = np.sqrt(np.mean(boosted_data**2))

    # Convert RMS to Decibels (dBFS)
    # A full-scale sine wave has an RMS of 0.707 (which we consider 0 dBFS max)
    if rms > 0:
        db = 20 * np.log10(rms)
    else:
        db = -100 # Silence

    # Apply Noise Gate logic to the actual saved audio frames
    # If the volume is below the threshold, silence the frame entirely
    if db < noise_gate_db:
        boosted_data.fill(0.0)

    # Normalize dB to a 0-100 percentage for the UI
    # Let's say -50 dB is 0% (silence/background noise), and 0 dB is 100% (clipping loud)
    min_db = -50
    max_db = 0
    percent = ((db - min_db) / (max_db - min_db)) * 100
    percent = np.clip(percent, 0, 100)

    # Smooth the fall-off (Peak Hold) so the meter doesn't instantly drop to 0 between syllables
    if percent > current_volume_rms:
        current_volume_rms = float(percent) # instant jump up
    else:
        current_volume_rms = float(current_volume_rms * 0.8 + percent * 0.2) # smooth glide down

    if recording_state["is_recording"]:
        recording_state["frames"].append(boosted_data.copy())

@eel.expose
def get_current_volume():
    """Returns the current smoothed 0-100 VU percentage."""
    return current_volume_rms

@eel.expose
def start_recording(profile_name, phrase_index):
    """Starts capturing audio from the default microphone."""
    if recording_state["is_recording"]:
        return

    print_and_log(f"Started recording phrase {phrase_index} for profile: {profile_name}")
    recording_state["frames"] = []
    recording_state["current_profile"] = profile_name
    recording_state["current_phrase"] = phrase_index
    recording_state["is_recording"] = True

    try:
        recording_state["stream"] = sd.InputStream(
            samplerate=recording_state["sample_rate"],
            channels=1,
            device=recording_state["device_id"],
            callback=audio_callback
        )
        recording_state["stream"].start()
    except Exception as e:
        log_error(f"Failed to start audio stream: {e}")
        recording_state["is_recording"] = False

@eel.expose
def stop_recording():
    """Stops the audio stream and saves the .wav file."""
    if not recording_state["is_recording"]:
        return False

    recording_state["is_recording"] = False

    try:
        if recording_state["stream"]:
            recording_state["stream"].stop()
            recording_state["stream"].close()
            recording_state["stream"] = None

        if not recording_state["frames"]:
            log_error("No audio frames captured.")
            return False

        # Combine all audio chunks
        # squeeze() ensures it's a 1D array if channels=1 was shaped (N, 1)
        audio_data = np.concatenate(recording_state["frames"], axis=0).squeeze()

        if len(audio_data) > 0:
            if use_spectral_nr:
                # Spectral Noise Reduction via STFT
                # Assume the first 0.3 seconds are "silence/room noise" before the user speaks
                noise_sample_len = int(0.3 * recording_state["sample_rate"])
                if len(audio_data) > noise_sample_len * 2:
                    noise_sample = audio_data[:noise_sample_len]

                    # Perform Short-Time Fourier Transform
                    f, t, Zxx = signal.stft(audio_data, fs=recording_state["sample_rate"], nperseg=1024)

                    # Get the noise profile (average magnitude across the noise sample's STFT frames)
                    _, _, Zxx_noise = signal.stft(noise_sample, fs=recording_state["sample_rate"], nperseg=1024)
                    noise_mag = np.mean(np.abs(Zxx_noise), axis=1, keepdims=True)

                    # Spectral Subtraction: Subtract noise magnitude from signal magnitude
                    sig_mag = np.abs(Zxx)
                    sig_phase = np.angle(Zxx)

                    # Oversubtraction factor to aggressively kill hiss (e.g. 2.0), and a spectral floor to prevent musical noise
                    alpha = 2.0
                    spectral_floor = 0.05 * noise_mag

                    clean_mag = sig_mag - (alpha * noise_mag)
                    clean_mag = np.maximum(clean_mag, spectral_floor)

                    # Reconstruct complex STFT and perform Inverse STFT
                    Zxx_clean = clean_mag * np.exp(1j * sig_phase)
                    _, audio_data = signal.istft(Zxx_clean, fs=recording_state["sample_rate"])

            # Apply High-Pass Filter (80Hz cutoff) to remove low-frequency rumble
            nyquist = 0.5 * recording_state["sample_rate"]
            cutoff = 80.0 / nyquist
            b, a = signal.butter(4, cutoff, btype='high', analog=False)
            audio_data = signal.filtfilt(b, a, audio_data)

            # Ensure it stays within safe float32 bounds after filtering
            audio_data = np.clip(audio_data, -1.0, 1.0)

        # Create user directory if it doesn't exist
        safe_name = "".join([c for c in recording_state["current_profile"] if c.isalpha() or c.isdigit() or c==' ']).rstrip()
        save_dir = os.path.join("voice_samples", safe_name)
        os.makedirs(save_dir, exist_ok=True)

        # Save to .wav
        filename = os.path.join(save_dir, f"phrase_{recording_state['current_phrase']}.wav")
        wav.write(filename, recording_state["sample_rate"], audio_data.astype(np.float32))

        print_and_log(f"Successfully saved voice sample: {filename}")
        return True

    except Exception as e:
        log_error(f"Failed to stop and save recording: {e}")
        return False

@eel.expose
def cancel_recording():
    """Stops the stream but intentionally discards the data (used for re-records)."""
    recording_state["is_recording"] = False
    if recording_state["stream"]:
        try:
            recording_state["stream"].stop()
            recording_state["stream"].close()
        except:
            pass
    recording_state["stream"] = None
    recording_state["frames"] = []
    print_and_log("Recording cancelled/discarded.")


def generate_presence_message(event_type):
    """
    Called when a wakeup event occurs after being away, or a manual leave event occurs.
    It prompts the LLM for a quick, dynamic JARVIS-like greeting/farewell based on time.
    """
    now = datetime.now()
    current_time_str = now.strftime("%I:%M %p")

    if event_type == "wakeup":
        prompt = f"The user has just returned to their desk. The current time is {current_time_str}. Give a short, futuristic, JARVIS-like greeting to welcome them back."

        # Execute dynamically enabled tools to build the briefing report
        reports = []
        for tool_name, is_enabled in briefing_prefs.items():
            if is_enabled:
                script_path = os.path.join("tools", tool_name, "main.py")
                if os.path.exists(script_path):
                    try:
                        print_and_log(f"Executing tool script: {script_path}")
                        # Setup subprocess flags to hide terminal window on Windows
                        creationflags = 0
                        if os.name == 'nt':
                            creationflags = subprocess.CREATE_NO_WINDOW

                        # Ensure we use 'python' to execute the sub-tool so it can print output safely,
                        # avoiding crashes if the main app was launched with pythonw
                        python_exe = sys.executable.replace("pythonw.exe", "python.exe")

                        # Run the tool and capture its output
                        result = subprocess.run(
                            [python_exe, script_path, "--report"],
                            capture_output=True,
                            text=True,
                            timeout=5,
                            creationflags=creationflags
                        )

                        if result.returncode == 0 and result.stdout.strip():
                            reports.append(result.stdout.strip())
                        else:
                            log_error(f"Tool {tool_name} returned an error or empty output: {result.stderr}")
                    except Exception as e:
                        log_error(f"Failed to execute tool {tool_name}: {e}")

        if reports:
            prompt += " As part of your greeting, seamlessly weave in the following data points into a short briefing report: \n"
            for r in reports:
                prompt += f"- {r}\n"
            prompt += "\nFormat it smoothly as spoken dialogue and end by asking if they need anything else."

        prompt += " Do not use tools or JSON, just return the plain text spoken dialogue."

    elif event_type == "leaving":
        prompt = f"The user is leaving their desk. The current time is {current_time_str}. Give a short, futuristic, JARVIS-like farewell. Do not use tools, just return the plain text farewell."
    else:
        return

    try:
        # Fetch model
        models = client.models.list()
        if not models.data: return
        model_id = models.data[0].id

        # We don't want this in the main conversation history to pollute it,
        # so we send a one-off request.
        temp_history = [
            {"role": "system", "content": load_system_prompt()},
            {"role": "user", "content": prompt}
        ]

        # Trigger UI to show talking state in OBS
        try: eel.setNovaState('talking')()
        except: pass

        response = client.chat.completions.create(
            model=model_id,
            messages=temp_history,
            temperature=0.8
        )

        ai_text = response.choices[0].message.content
        print_and_log(f"NOVA (Presence): {ai_text}")

        # Push message directly to the chat UI and history
        conversation_history.append({"role": "assistant", "content": ai_text})

        # We wrap these in separate try/except blocks because Eel broadcasts to all open HTML windows.
        # pushAIMessage exists in index.html but not obs_overlay.html, so it will throw an exception there.
        # We don't want that exception to stop the OBS state from reverting to idle.
        try: eel.pushAIMessage(ai_text)()
        except Exception as e: pass

        try: eel.setNovaState('idle')()
        except Exception as e: pass

    except Exception as e:
        log_error(f"Failed to generate presence message: {e}")


class PresenceRequestHandler(BaseHTTPRequestHandler):
    def _send_response(self, status, message):
        self.send_response(status)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        if message:
            self.wfile.write(json.dumps(message).encode('utf-8'))

    def do_GET(self):
        if self.path == '/obs':
            global dynamic_ui_port
            if dynamic_ui_port:
                # 302 Redirect to the dynamic OBS overlay URL
                redirect_url = f"http://127.0.0.1:{dynamic_ui_port}/obs_overlay.html"
                self.send_response(302)
                self.send_header('Location', redirect_url)
                self.end_headers()
            else:
                self._send_response(503, {"error": "UI Port not registered yet. Open the main NOVA app first."})
        else:
            self._send_response(404, {"error": "Not found"})

    def do_POST(self):
        global dynamic_ui_port

        if self.path == '/register_port':
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length > 0:
                post_data = self.rfile.read(content_length)
                try:
                    data = json.loads(post_data.decode('utf-8'))
                    port = data.get('port')
                    if port:
                        dynamic_ui_port = port
                        print_and_log(f"Dynamic UI port registered: {port}")
                        self._send_response(200, {"status": "success"})
                    else:
                        self._send_response(400, {"error": "Missing port"})
                except json.JSONDecodeError:
                    self._send_response(400, {"error": "Invalid JSON"})

        elif self.path == '/presence':
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length > 0:
                post_data = self.rfile.read(content_length)
                try:
                    data = json.loads(post_data.decode('utf-8'))
                    event = data.get('event')
                    now = time.time()

                    if event == "sleep":
                        print_and_log("[PRESENCE API] User has gone idle/left (Sleep mode).")
                        presence_state["is_present"] = False
                        presence_state["last_event_time"] = now
                        try: eel.addActivityLog('system', "Vision system: User absent. Sleep mode activated.")()
                        except: pass

                    elif event == "wakeup":
                        print_and_log("[PRESENCE API] User returned (Wakeup mode).")
                        time_away = now - presence_state["last_event_time"]

                        if not presence_state["is_present"] or time_away > 120:
                            print_and_log(f"[PRESENCE API] User was away for {int(time_away)}s. Triggering greeting.")
                            try: eel.addActivityLog('system', "Vision system: User returned. Generating greeting.")()
                            except: pass
                            threading.Thread(target=generate_presence_message, args=("wakeup",), daemon=True).start()

                        presence_state["is_present"] = True
                        presence_state["last_event_time"] = now
                        presence_state["last_seen"] = now

                    elif event == "leaving":
                        print_and_log("[PRESENCE API] User is actively leaving.")
                        presence_state["is_present"] = False
                        presence_state["last_event_time"] = now
                        try: eel.addActivityLog('system', "Vision system: User actively leaving. Generating farewell.")()
                        except: pass
                        threading.Thread(target=generate_presence_message, args=("leaving",), daemon=True).start()

                    self._send_response(200, {"status": "success", "event": event})
                except json.JSONDecodeError:
                    self._send_response(400, {"error": "Invalid JSON"})
            else:
                self._send_response(400, {"error": "Missing payload"})
        else:
            self._send_response(404, {"error": "Not found"})

def run_presence_server():
    port = 54321
    server = HTTPServer(('127.0.0.1', port), PresenceRequestHandler)
    print_and_log(f"Starting local webhook presence API on http://127.0.0.1:{port}/presence")
    server.serve_forever()


def start_app():
    # Start the webhook API in a daemon thread so it dies when the main app closes
    threading.Thread(target=run_presence_server, daemon=True).start()

    # Start the OBS background monitor
    threading.Thread(target=monitor_obs_process, daemon=True).start()

    # Initialize eel pointing to our 'web' folder
    eel.init('web')

    print_and_log("NOVA UI Initialized. Launching window...")

    # Start the app. You can tweak geometry here.
    # port=0 forces the OS to pick a random available port, preventing 'Address already in use' errors.
    try:
        eel.start('index.html', size=(900, 700), position=(100, 100), port=0)
    except (SystemExit, KeyboardInterrupt):
        print_and_log("NOVA shut down.")

if __name__ == '__main__':
    start_app()
