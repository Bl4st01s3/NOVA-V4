NOVA D3D Autonomous Intelligence - Project Overview

## What is NOVA?
NOVA is an Agentic Loop AI assistant built for the Dark 3rd Dimension (D3D) digital fabrication and electronics lab. It is designed to run completely locally on a desktop environment utilizing heavy GPU offloading.
Nova acts as a highly efficient, hyper-polite British butler serving a chaotic engineer (inspired by Jarvis). She is dry, witty, slightly condescending, and strictly adheres to this persona.

## System Architecture
The system uses a modular, local-first architecture powered by Eel (Python backend) and HTML/JS (Frontend UI).

*   **Central Hub (`main.py`)**: The orchestrator. Receives input, manages state, and handles conversation memory. It passes requests to the LLM, parses the resulting JSON schemas, and dispatches tool execution tasks.
*   **Asynchronous ReAct Loop**: For long-running tool execution, the Hub implements a two-pass architecture. It provides an immediate, low-latency verbal affirmation (e.g., "Right away, sir.") while the long-running task executes in the background. Once the task completes, the results are passed back to the LLM to generate the final verbal report.
*   **LLM Reasoning Node**: Operates 100% locally via the LM Studio ('Bionic') engine. `run.bat` automatically forces the LLM (e.g., Llama 3.1 8B Q4_K_M) entirely into GPU VRAM (`--gpu max`) before launching the UI to guarantee zero TTFT latency.
*   **Tool Execution Node (`tools/*/main.py`)**: A dynamic plugin manager. Tools are loaded autonomously on boot. The system reads `schema.json` to instruct the LLM, `about.txt` to inject tool awareness into the system prompt, and `config.json` to apply phonetic TTS overrides.
*   **Audio Output / TTS Node**: Uses a dedicated background worker (`tts_worker`) running `pyttsx3` to generate neural voices without blocking the UI thread. Processes audio with dynamically configured DSP math (Futuristic, Robotic, or Natural effects) using `numpy` and `scipy`.

## Settings & Audio Control Center
The Hub serves a highly interactive Web UI which acts as the mission control for Nova's sensory I/O.
*   **Hardware Routing**: Dynamically queries `sounddevice` to populate literal hardware names for Microphone selection, overriding buggy OS defaults.
*   **Signal Processing**: Provides UI sliders to manipulate variables for hardware Input Gain multipliers, Noise Gate thresholds, and STFT Spectral Noise Reduction (Anti-Hiss).

## STT & Biometric Voice Prints (Phase 1.5 / 2.0)
NOVA is transitioning to a hands-free, voice-activated interface. To prevent background noise (like TVs or 3D printers) from triggering commands, the system relies on Biometric Voice Profiles rather than simple wake words.
*   **Enrollment Wizard**: Users read specific pangrams into the UI.
*   **Acoustic Embeddings**: The raw `.wav` audio is stripped of hardware hiss via Spectral Subtraction, filtered with an 80Hz High-Pass, and permanently saved. Future updates will process these clean samples into mathematical acoustic embeddings for real-time Speaker Verification.

## Plugins & Capabilities

### Currently Implemented Tools
*   **Weather (`weather`)**: Fetches current real-time local weather data.
*   **Calendar (`calendar`)**: Checks the user's local schedule for upcoming meetings and appointments.
*   **Nervous System (`nervous_system`)**: Queries a Banana Pi for offline background events (security logs, temperature, power cuts).
*   **OctoPrint (`octoprint`)**: Checks 3D printer status (currently a placeholder preventing AI hallucination).

### Future Roadmap & Planned Tools
*   **Calculator**: Safely evaluate math expressions using `ast`.
*   **Time / World Clock**: Handle timezone conversions using `pytz` and `dateutil`.
*   **Advanced Printer Control**: Full Moonraker/Klipper/OctoPrint integration to read print progress, query hotend/bed temps, and ping LDO BoxTurtle MMUs for filament jams. Includes two-step verified print cancellations.
*   **System Control**: Lifecycle management to `stop_software`, `power_off_device`, `restart_software`, and perform `update_software` via `git`.
*   **Long-Term Memory Manager**: Save user facts and preferences to `long_term_memory.json` to be automatically injected into the system prompt.
*   **WLED Control**: Trigger an "Aesthetic Override" to instantly set the lab to the default cyan and purple dark mode.
*   **Audio & Media**: Voice-controlled Spotify playback, volume control, and quick-starting specific playlists.
*   **Digital Routing**: Trigger CyberSync Command Console macros for switching PC displays or muting microphones.
*   **Timers & Bench Math**: Set audible timers (e.g., for curing epoxy) and perform hands-free electronics calculations (voltage drops, resistor values).
*   **Sassy Stream Co-Host**: Read highlighted Twitch chat questions out loud in her deadpan persona, and trigger stream sound effects.
*   **Gridfinity Locator**: A JSON database mapping 3x4 drawer layouts to locate specific components like ESP32 boards.
*   **Workstation Diagnostics**: Query the main PC to read GPU thermals and processing loads during heavy CAD rendering.
*   **Hobby API Hooks**: Fast Yu-Gi-Oh!/Pokedex database queries to read card text without alt-tabbing.
*   **Hands-Free Multimeter**: A networked ESP32-S2 acting as a logic probe to read voltages or PWM signals out loud.
*   **Physical Stream Anomalies**: Hooking Twitch events into the physical lab (e.g., a new subscriber causes lab lights to flicker and an audible power-drain hum).
*   **Klipper Red Alerts**: If a thermal runaway or severe layer shift occurs while live, NOVA interrupts the stream, flashes the lab lights red, and announces the failure in character.
*   **Rocket Launch Tracker**: Check APIs for SpaceX, Blue Origin, ESA, etc., to announce upcoming mission schedules and goals.
*   **Dual Input Pipelines**: Maintain separate processing queues for user microphone input vs. automated system alerts/warnings.
*   **Automated 3D Model Publisher**: A watcher tool for a specific directory where 3D models, pictures, and markdown descriptions can be dropped. NOVA will automatically process the folder and post the assets to 3D printing distribution sites (Printables, MakerWorld, Thingiverse, etc.).