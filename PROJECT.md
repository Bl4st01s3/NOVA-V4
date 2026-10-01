NOVA D3D Autonomous Intelligence - Project Overview

What is NOVA?
NOVA is an Agentic Loop AI assistant built for the Dark 3rd Dimension (D3D) digital fabrication and electronics lab. It is designed to run locally.
Nova acts as a highly efficient, hyper-polite British butler serving a chaotic engineer (inspired by Jarvis). She is dry, witty, slightly condescending, and strictly adheres to this persona.

System Architecture
The system uses a modular architecture.
Central Hub (`main.py`): The orchestrator. Receives input, manages state, and manages conversation memory. It passes requests to the LLM, parses the resulting JSON, and dispatches tool execution tasks.
Hub Firewall: Actively inspects outgoing tool requests. It enforces an `ALLOWED_TOOLS` whitelist and physically blocks destructive actions (like 3D printer cancellation) if strict confirmation flags are missing.
Two-Pass ReAct Loop: If the LLM generates a tool plan, the Hub executes the tools and sends the results back to the LLM in a second prompt to prevent hallucinations, enforcing strict JSON output.
LLM Reasoning Node: A Multi-Engine backend connected to LM Studio via the OpenAI SDK.
Local: Uses LM Studio ('Bionic') backend for 100% offline GGUF execution.
Tool Execution Node (`tools/*/main.py`): A plugin manager that dynamically loads and executes Python scripts located in `tools/`.
Audio Input / STT Node: Captures real-time audio using `sounddevice`. Implements Spectral Noise Reduction and Noise Gate.
Audio Output / TTS Node: Uses pyttsx3 to generate neural voices. Processes audio with dynamically configured DSP effects (like Futuristic or Robotic).

Settings & Audio Control Center
The Hub serves an Eel Web UI which acts as the mission control for Nova's sensory I/O.
Hardware Routing: Dynamically queries ALSA/SoundDevice to populate literal hardware names for Microphone selection, overriding buggy generic default routing.
Signal Processing: Provides UI sliders to manipulate variables for hardware Input Gain multipliers, VU Meter visual sensitivity, and DSP Audio Output logic.

Plugins & Capabilities
Plugins are python files in `tools/` containing a `run()` function. Current and past plugins include:
`calculator.py`: Safely evaluates math expressions using `ast`.
`get_time.py`: Returns the system time.
`list_tools.py`: Introspects available python plugins.
`world_clock.py` / `time_calculator.py`: Handles timezone conversions using `pytz` and `dateutil`.
`printer_control.py`: Controls Moonraker/Klipper 3D printers. Supports status queries, temperature setting, and two-step verified print cancellations.
`system_control.py`: Lifecycle management. Can `stop_software`, `power_off_device`, `restart_software`, and `update_software`.
`memory_manager.py`: Long-term persistent memory. Saves user facts and preferences to `long_term_memory.json`. The Hub automatically injects these into the LLM system prompt on every request.

Current Limitations & Roadmap:
* Voice Identification (Speaker Recognition) using biometric embeddings is planned for a future update.
* Raspberry pi Zero 2w Physical UI: drive a 7" screen in kiosk mode and connect to the NOVAs WebSocket and manually render the animated UI orb based on raw VU/state telemetry.

Ideas for Future tools, scripts and functions
Feature list:
* Read print 3d progress, query hotend/bed temps, and ping the LDO BoxTurtle MMU for filament jams or runouts.
* WLED (color/brightness) and trigger an "Aesthetic Override" to instantly set the lab to the default cyan and purple dark mode.
* Audio & Media: Voice-controlled Spotify/local playback, including volume control and quick-starting heavy metal or epic rock playlists.
* Digital Routing: Trigger basic CyberSync Command Console macros for switching PC displays or muting your microphone.
* Timers & Quick Math: Set audible timers for curing epoxy and perform hands-free bench math (e.g., calculating voltage drops or resistor values).
* Sassy Stream Co-Host: An MCP tool reading the Twitch API, allowing you to ask NOVA to read highlighted chat questions out loud in her deadpan, British-butler persona, plus vocal triggers for stream sound effects.
* Gridfinity Locator: A JSON database mapping your 3x4 drawer layouts so you can ask NOVA exactly which block and row holds specific components like your ESP32-S2 boards.
* Workstation Diagnostics: Querying your main PC to read the thermals and current processing load of your GPU during heavy CAD rendering.
* Hobby API Hooks: Fast Yu-Gi-Oh! database queries to read the exact text of cards like Silent Magician without alt-tabbing out of Master Duel. Pokedex Look up and query
* Hands-Free Multimeter: A networked ESP32-S2 acting as a logic probe, allowing you to clip a wire and ask NOVA to read the voltage or PWM signal out loud while both your hands are full.
* Physical Stream Anomalies: Hooking Twitch events into the physical lab—such as a new subscriber causing the lab lights to flicker and an audible power-drain hum to play while NOVA announces the "unauthorized power diversion."
* Klipper Red Alerts: If Klipper detects a thermal runaway or severe layer shift while live, NOVA interrupts the stream, flashes the lab lights red, and announces the failure in character.
* Open 2 input pipe lines, user inputs from the microphone and system inputs for warnings and alerts and announcements
* next_rocket_launch.py: checks an API to see when the next rocket launch is scheduled for and maybe what the mission is and information on what the mission is intended to accomplish, NASA, spaceX, BlueOrigen, ESA, Russian and Chinese space agencies (check all that could launch a rocket)
* Time and Date
* Weather
* Timer
* Music Controller
* Home Automation
* Calendar
* News (General and Hobby Related)
* Unit_Converter
* Translator
* Machine Learning
* System Status
* Google Alert Monitoring
* Youtube and Twitch Live Stream and New video Alerts
* Dictionary Look Up
* Thesaurus
* 3D Printer Control
* Desk Control
* Amazon Fire Stick Control
* Tv Control
* Stream Co host Mode
* Self Back Up
* ESPNow Communication Controller
* Bluetooth Communication Controller
* Sensor Data Collection
* Function Scheduler
* Presence Detection
* Order Tracking
* Medication reminder
* Medication order reminder

** NOTES **
* Make the UI maintain chat history better launches
* add a Config button and Privacy tick box for every tool in the tools Tab (config button to open a window that lets us adjust the configuration of the tool, the privacy tick box to make the system block the tool when streamer mode is activated)
* block multiple instances of NOVA running at once
