# NOVA - Personal AI Assistant

NOVA is a personal AI assistant project designed to provide a "Jarvis-like" experience running entirely locally on your PC. It acts as an advanced wrapper and embodiment for the LM Studio ("Bionic") LLM engine, giving you the intelligence of models like Llama 3.1 8B completely free, offline, and private.

## Core Features & Architecture

* **Local Execution**: Connects to LM Studio's OpenAI-compatible local server (`localhost:1234`).
* **Futuristic UI**: A cyberpunk-inspired HTML/CSS/JS frontend served by a Python `Eel` backend, featuring custom SVG cursors, glowing neon accents, and hexagonal geometry.
* **Invisible Operation**: NOVA runs silently in the background. Launching `run.bat` uses `pythonw.exe` to hide the terminal window, redirecting all standard output to a centralized `nova.log` file.
* **Dynamic Porting**: To avoid `WinError 10048` (Address already in use) crashes, NOVA's UI launches on a random dynamic port (`port=0`).

---

## 🎥 OBS Stream Overlay Integration

NOVA includes an HTML5 Canvas visual embodiment designed to be overlaid onto your Twitch/YouTube live streams via OBS Studio.

* **Visuals**: A breathing central orb with internal nodes, orbiting satellite particles, and an active oscilloscope wave. The UI dynamically changes colors based on NOVA's real-time state: Cyan (Idle), Purple (Talking), Red (Error).
* **Setup**: Add a "Browser Source" in OBS and point it to the static redirect URL:
  ```
  http://127.0.0.1:54321/obs
  ```
* **How it works**: Because the main UI port changes every launch, the background webhook server (running permanently on `54321`) intercepts requests to `/obs` and silently redirects OBS to the correct dynamic port for that specific session. You only have to enter the URL into OBS once.

---

## 📡 Presence Webhook API & Modular Briefings

NOVA includes a lightweight background API running on port `54321` designed to ingest external events (e.g., from local camera vision systems like "Cybermouse").

**Endpoint:** `POST http://127.0.0.1:54321/presence`
**Payload:** `{"event": "<action>"}`

* **`"sleep"`**: Tells NOVA you left the room. She silently updates her state to 'Away'.
* **`"wakeup"`**: Tells NOVA you sat down. If you were gone for > 2 minutes, she intercepts the event and dynamically generates a personalized, time-aware greeting report.
* **`"leaving"`**: Triggers an instant farewell sequence.

### Modular Tools (`/tools`)
When NOVA generates a `"wakeup"` greeting, she can dynamically weave real-world data into her speech.
1. Create a new folder in the `tools/` directory (e.g., `tools/smart_lights`).
2. Add a `main.py` file that prints data to the console (e.g., `print("Lights are on in the kitchen.")`).
3. Open NOVA's UI, navigate to the **Settings** tab, and toggle the new tool checkbox that automatically appears.
4. When you sit down, NOVA executes the tool invisibly in the background and includes the data in her "Welcome Back" briefing!

---

## 🎙️ Voice Profiles & Acoustic Enrollment (Phase 1.5)

NOVA includes a multi-user Voice Profile Manager designed to distinguish between users and ignore background noise (like a TV).

* **Enrollment Wizard**: Found in the Settings tab, this UI guides you through reading specific pangrams (e.g., *"Sphinx of black quartz, judge my vow"*).
* **Live Hardware Capture**: Utilizing `sounddevice`, you can select your exact input microphone via a dropdown. A live VU meter ensures audio is being captured correctly.
* **Data Storage**: Raw `.wav` recordings are permanently saved into the `voice_samples/<Profile Name>/` directory, while metadata is secured in `voice_profiles.json`. This physical audio data prepares the repository perfectly for the upcoming Phase 2 (Local STT/TTS & Speaker Verification Embedding).

---

## Setup and Running

1. Run `setup.bat` to build the Python Virtual Environment and install dependencies.
2. Run `run.bat` to launch the LM Studio server and open the NOVA UI silently in the background.
3. Check `nova.log` in the root directory for any debugging or error output.
