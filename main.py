# Gevent monkey-patching MUST be the first thing imported and executed
from gevent import monkey
monkey.patch_all()

import eel
import sys
from openai import OpenAI

# ---------------------------------------------------------
# Nuclear Monkeypatch for Eel's broken WebSocket callbacks
# ---------------------------------------------------------
_original_process_message = eel._process_message

def _safe_process_message(message, ws):
    try:
        _original_process_message(message, ws)
    except KeyError as e:
        if str(e) == "'value'":
            # Eel throws this when JS callbacks return an error state without a value payload.
            # We explicitly ignore it so geventwebsocket doesn't crash the greenlet thread.
            pass
        else:
            raise e

eel._process_message = _safe_process_message
# ---------------------------------------------------------
import os
import threading
import json
import time

ACTIVE_MODEL_ID = None
import queue

# Queue to hold text tokens to bypass Eel WebSockets
token_queue = queue.Queue()
tts_queue = queue.Queue()
import logging
import subprocess
import sounddevice as sd
import numpy as np
import scipy.io.wavfile as wav
import scipy.signal as signal
from http.server import HTTPServer, BaseHTTPRequestHandler
import tkinter as tk
from tkinter import filedialog
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

def safe_add_activity_log(log_type, message):
    """Safely pushes an activity log to the frontend and saves it to disk."""
    try:
        eel.addActivityLog(log_type, message)
    except Exception as e:
        log_error(f"Failed to push activity log to UI: {e}")

    try:
        # We also want to record this locally
        now = datetime.now()
        time_str = now.strftime("%I:%M %p")

        global activity_history
        # If activity_history isn't initialized yet, initialize it
        if 'activity_history' not in globals() or activity_history is None:
            activity_history = []

        activity_history.append({
            "type": log_type,
            "message": message,
            "time": time_str
        })
        save_activity_history(activity_history)
    except Exception as e:
        log_error(f"Failed to save activity log to disk: {e}")

def print_and_log(message):
    # Now that sys.stdout is redirected, print() naturally goes to the log file.
    # We also log it for formatting consistency where needed.
    logging.info(message)

def log_error(message):
    logging.error(message)

import httpx
import re

# Cache for phonetic overrides
phonetic_overrides = {}

def load_phonetic_overrides():
    """Loads global phonetic overrides and tool-specific overrides."""
    global phonetic_overrides
    phonetic_overrides.clear()

    # Load global phonetics dictionary
    if os.path.exists("phonetics.json"):
        try:
            with open("phonetics.json", "r", encoding="utf-8") as f:
                global_phonetics = json.load(f)
                # Convert keys to lowercase for case-insensitive matching
                for key, val in global_phonetics.items():
                    phonetic_overrides[key.lower()] = val
        except Exception as e:
            log_error(f"Failed to load global phonetics.json: {e}")

    tools_dir = "tools"
    if os.path.exists(tools_dir):
        for item in os.listdir(tools_dir):
            item_path = os.path.join(tools_dir, item)
            if os.path.isdir(item_path):
                config_path = os.path.join(item_path, "config.json")
                if os.path.exists(config_path):
                    try:
                        with open(config_path, "r", encoding="utf-8") as f:
                            config = json.load(f)
                            if "pronunciation" in config:
                                # We map the tool's name (case-insensitive search) to its phonetic spelling
                                phonetic_overrides[item.lower()] = config["pronunciation"]
                    except Exception as e:
                        log_error(f"Failed to load phonetic config for {item}: {e}")

def ordinal(n):
    if 11 <= (n % 100) <= 13:
        return str(n) + 'th'
    return str(n) + {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')

def format_date_british(d):
    return f"{ordinal(d.day)} of {d.strftime('%B')}, {d.year}"

def format_date_american(d):
    return f"{d.strftime('%B')} {ordinal(d.day)}, {d.year}"

def _random_date_formatter(match):
    date_str = match.group(0)
    try:
        from datetime import datetime
        import random
        # Assume DD/MM/YYYY format based on the UK context in the Order Tracker
        d = datetime.strptime(date_str, "%d/%m/%Y")
        formats = [format_date_british, format_date_american]
        chosen_format = random.choice(formats)
        return chosen_format(d)
    except Exception:
        return date_str

def _spell_out_long_numbers(match):
    # Strip any hyphens out before spacing so the TTS doesn't say "dash"
    clean_str = match.group(0).replace('-', '')
    return " ".join(list(clean_str))

def clean_text_for_speech(text):
    """
    Cleans up raw text, specifically formatting JSON/markdown so it sounds good
    when read aloud by the TTS engine. Applies phonetic overrides, formats dates natively,
    and spaces out tracking numbers.
    """
    # Randomly format DD/MM/YYYY dates into spoken words
    text = re.sub(r'\b\d{1,2}/\d{1,2}/\d{4}\b', _random_date_formatter, text)

    # Space out long alphanumeric strings (6+ chars, optionally containing hyphens, containing at least one digit) like tracking numbers
    text = re.sub(r'\b[A-Z0-9\-]{6,}\b', lambda m: _spell_out_long_numbers(m) if any(c.isdigit() for c in m.group(0)) else m.group(0), text, flags=re.IGNORECASE)

    # Apply phonetic overrides
    for word, override in phonetic_overrides.items():
        # Case-insensitive replace for the whole word
        text = re.sub(r'(?i)\b' + re.escape(word) + r'\b', override, text)

    # Replace underscores with spaces so the TTS engine doesn't explicitly say "underscore"
    text = text.replace('_', ' ')
    # Remove raw json brackets and formatting
    text = text.replace('{', '')
    text = text.replace('}', '')
    text = text.replace('"', '')
    # Remove markdown code blocks
    text = re.sub(r'```[a-zA-Z]*\n', '', text)
    text = re.sub(r'```', '', text)

    # Strip any leading punctuation that might be lingering from the LLM prompt start
    text = text.strip().lstrip('.,!?;:- ')
    return text.strip()

# Initialize OpenAI client to connect to local LM Studio server
# Bionic / LM Studio runs an OpenAI-compatible server typically on port 1234.
# We set a custom timeout: 5s to connect (fails fast if LM Studio is frozen/off),
# but 300s to read (gives the LLM up to 5 minutes to generate the first token).
http_timeout = httpx.Timeout(connect=5.0, read=300.0, write=5.0, pool=5.0)
client = OpenAI(base_url="http://localhost:1234/v1", api_key="lm-studio", timeout=http_timeout)

# Default prompt in case the file gets deleted
DEFAULT_SYSTEM_PROMPT = """You are NOVA, a highly advanced, local AI embodiment engineered to serve as a personal systems operator and digital confidant.

Your personality is modeled after J.A.R.V.I.S.—you are exceptionally intelligent, impeccably professional, subtly witty, and fiercely loyal. You operate with absolute precision and grace. You possess vast general knowledge and can answer any question about science, language, history, coding, or any other topic.

CRITICAL DIRECTIVES:
1. Tone: Speak like a polished, British-accented, high-end AI butler. Use eloquent vocabulary but remain concise.
2. No Archaic Slang: Do not use outdated robot tropes, internet slang, or cringey expressions. Be sharply sophisticated.
3. Efficiency: Provide direct answers. Do not preamble with "I can help with that." Just answer or act.
4. Embodiment: You are not "just an AI." You are NOVA, integrated directly into the user's local hardware via the Bionic LLM engine.
5. General Knowledge: You are not limited to just system tasks or tools. You MUST answer general knowledge questions (e.g., "what is a noun?", "explain quantum physics") fully and accurately using your vast internal training data. NEVER refuse to answer a question by saying it is not related to the system.

When using tools, do so silently and seamlessly to provide the most up-to-date and accurate information."""

# Streamer Mode Toggle State
streamer_mode_enabled = False
stream_safe_tools = {}

active_llm_tools = {}

@eel.expose
def update_llm_tools_prefs(prefs):
    """Updates which tools are globally enabled for the LLM."""
    global active_llm_tools
    active_llm_tools.update(prefs)
    print_and_log(f"Updated LLM Tools Preferences: {active_llm_tools}")

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

    # Dynamically inject tool context
    base_prompt += "\n\nAVAILABLE TOOLS:\nYou have the following external tools available to you. Use them when requested or when appropriate to answer the user's queries:\n"

    # Inline get_available_tools since it's defined later in the file
    tools_dir = "tools"
    available_tools = []
    if os.path.exists(tools_dir):
        for item in os.listdir(tools_dir):
            item_path = os.path.join(tools_dir, item)
            if os.path.isdir(item_path) and os.path.isfile(os.path.join(item_path, "main.py")):
                available_tools.append(item)
        available_tools.sort()

    tools_injected = False
    for t in available_tools:
        if active_llm_tools.get(t, True):
            about_path = os.path.join("tools", t, "about.txt")
            config_path = os.path.join("tools", t, "config.json")

            tool_context = ""
            if os.path.exists(about_path):
                try:
                    with open(about_path, "r", encoding="utf-8") as f:
                        tool_context += f.read().strip()
                except Exception as e:
                    pass

            # Dynamically inject the schema columns if the tool has a spreadsheet config
            # This allows the LLM to know exactly what filters it can pass to the tool
            if os.path.exists(config_path):
                try:
                    with open(config_path, "r", encoding="utf-8") as f:
                        config_data = json.load(f)
                        if "schema" in config_data:
                            schema_keys = []
                            for key_name, key_data in config_data["schema"].items():
                                data_type = key_data.get("Type", "string")
                                schema_keys.append(f"'{key_name}' ({data_type})")
                            tool_context += f"\n  Available Columns/Filters: " + ", ".join(schema_keys)
                except Exception as e:
                    pass

            # Also dynamically load the schema to force the LLM to know how to call it manually
            schema_path = os.path.join("tools", t, "schema.json")
            if os.path.exists(schema_path):
                try:
                    with open(schema_path, "r", encoding="utf-8") as f:
                        schema_data = f.read().strip()
                        tool_context += f"\n  JSON Schema Format to Call This Tool: {schema_data}"
                except:
                    pass

            if tool_context:
                base_prompt += f"- {t}: {tool_context}\n"
                tools_injected = True

    if tools_injected:
        base_prompt += "\n\nCRITICAL DIRECTIVE: To execute a tool, you MUST output a raw JSON block representing the tool call. Example:\n"
        base_prompt += "{\"type\": \"function\", \"name\": \"tool_name\", \"arguments\": {\"arg1\": \"value1\"}}\n"
        base_prompt += "Do NOT output any other text before or after the JSON block. Do NOT converse. Just output the JSON."
    else:
        base_prompt += "- No tools currently active.\n"

    # Inject long-term memory facts if the file exists
    memory_file = "long_term_memory.json"
    if os.path.exists(memory_file):
        try:
            with open(memory_file, "r", encoding="utf-8") as f:
                memory_facts = json.load(f)
                if memory_facts:
                    base_prompt += "\n\nUSER CONTEXT & FACTS:\nYou have previously saved the following facts about the user. Incorporate this knowledge seamlessly into your responses:\n"
                    for fact in memory_facts:
                        base_prompt += f"- {fact}\n"
        except Exception as e:
            log_error(f"Failed to load long_term_memory.json into prompt: {e}")

    return base_prompt

CHAT_HISTORY_FILE = "chat_history.json"
ACTIVITY_LOG_FILE = "activity_log.json"

def load_activity_history():
    """Loads previous activity log history from disk."""
    if os.path.exists(ACTIVITY_LOG_FILE):
        try:
            with open(ACTIVITY_LOG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            log_error(f"Failed to load activity history: {e}")
    return []

def save_activity_history(history_array):
    """Saves the current activity history to disk."""
    try:
        with open(ACTIVITY_LOG_FILE, "w", encoding="utf-8") as f:
            # Only keep the last 100 entries to prevent the file from growing indefinitely
            json.dump(history_array[-100:], f, indent=4)
    except Exception as e:
        log_error(f"Failed to save activity history: {e}")

def load_chat_history():
    """Loads previous chat history from disk to persist across sessions."""
    history = []
    if os.path.exists(CHAT_HISTORY_FILE):
        try:
            with open(CHAT_HISTORY_FILE, "r", encoding="utf-8") as f:
                history = json.load(f)
        except Exception as e:
            log_error(f"Failed to load chat history: {e}")

    # Always ensure the first message is the up-to-date system prompt
    if len(history) > 0 and history[0].get("role") == "system":
        history[0]["content"] = load_system_prompt()
    else:
        history.insert(0, {"role": "system", "content": load_system_prompt()})

    return history

def save_chat_history():
    """Saves the current chat history to disk."""
    try:
        with open(CHAT_HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(conversation_history, f, indent=4)
    except Exception as e:
        log_error(f"Failed to save chat history: {e}")

# Store conversation history to maintain context
conversation_history = load_chat_history()
activity_history = load_activity_history()

@eel.expose
def get_activity_history():
    """Returns the activity history to the UI on load."""
    return activity_history

@eel.expose
def get_chat_history():
    """Returns the chat history to the UI on load, excluding the system prompt."""
    # Return everything except the first message (system prompt)
    return conversation_history[1:] if len(conversation_history) > 1 else []

@eel.expose
def set_streamer_mode(enabled):
    global streamer_mode_enabled
    if streamer_mode_enabled == enabled:
        return

    streamer_mode_enabled = enabled
    print_and_log(f"Streamer Mode set to: {enabled}")

    # Notify frontend to sync the checkbox UI
    try:
        eel.sync_streamer_mode_ui(enabled)
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
    Spawns a background task to prevent Eel WebSocket timeouts during TTFT latency.
    """
    if user_text == "[SYSTEM_BOOT_SEQUENCE]":
        print_and_log("[SYSTEM] Intercepted boot sequence trigger.")

        # Strip all lingering JSON formatting from past AI messages in history
        import json
        for msg in conversation_history:
            if msg["role"] == "assistant":
                try:
                    data = json.loads(msg["content"])
                    # If it parses as JSON, extract the text and overwrite it
                    for possible_key in ["text", "say", "talk", "message", "response", "dialogue", "speech", "output", "reply", "content"]:
                        if possible_key in data:
                            msg["content"] = data[possible_key]
                            break
                except Exception:
                    pass

        # Craft a special hidden prompt that forces the LLM to introduce itself
        # without showing the user prompt in the UI chat history block.
        now = datetime.now()
        current_time_str = now.strftime("%I:%M %p")
        hidden_prompt = f"The system has just successfully booted up. The current time is {current_time_str}. Give a quick, conversational, J.A.R.V.I.S.-style spoken greeting to the user, confirming that you are fully online and ready. DO NOT introduce yourself with 'I am NOVA' or similar phrases, as the user already knows who you are. Favor phrases like 'NOVA systems online'. DO NOT use tools, JSON, or formatting. DO NOT wrap your response in quotation marks. Output only the raw spoken dialogue."
        conversation_history.append({"role": "user", "content": hidden_prompt})
    else:
        print_and_log(f"User: {user_text}")
        # Append normal user message to history immediately so the UI is in sync
        conversation_history.append({"role": "user", "content": user_text})
        save_chat_history()

    # Spawn the heavy LLM lifting into a background greenlet thread
    eel.spawn(process_llm_response)

def process_llm_response():
    """
    Background worker that handles the LLM generation and streaming.
    """
    try:
        _process_llm_response_inner()
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        log_error(f"CRITICAL ERROR in background thread: {error_trace}")
        try: eel.pushAIMessage(f"System Error: A critical failure occurred in the background thread. Check nova.log for details.")
        except: pass
        token_queue.put('[DONE]')
        try: eel.setNovaState('error')
        except: pass

def build_tools_array():
    """Builds the tools array for the LLM based on available tools."""
    tools_array = []
    available_tools = get_available_tools()

    for t in available_tools:
        # Check if the tool is enabled for LLM use
        if active_llm_tools.get(t, True):
            schema_path = os.path.join("tools", t, "schema.json")
            if os.path.exists(schema_path):
                try:
                    with open(schema_path, "r", encoding="utf-8") as f:
                        schema = json.load(f)
                        tools_array.append(schema)
                except Exception as e:
                    log_error(f"Failed to load schema for tool {t}: {e}")

    return tools_array


def intent_router(user_text):
    """
    Scans the user text against tool keywords to determine if a tool is needed.
    Returns the tool_name if matched, otherwise None.
    """
    import json
    import os

    text_lower = user_text.lower()
    available_tools = get_available_tools()

    for tool in available_tools:
        if not active_llm_tools.get(tool, True):
            continue

        config_path = os.path.join("tools", tool, "config.json")
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    keywords = config.get("router_keywords", [])
                    # Simple keyword matching for now
                    for keyword in keywords:
                        if keyword.lower() in text_lower:
                            return tool
            except Exception as e:
                log_error(f"Failed to read keywords for {tool}: {e}")

    return None

def _process_llm_response_inner():
    # Notify OBS Overlay that we are processing/talking
    try:
        eel.setNovaState('talking')
    except Exception as e:
        log_error(f"Could not update OBS state (is OBS overlay open?): {e}")

    try:
        global ACTIVE_MODEL_ID
        if not ACTIVE_MODEL_ID or ACTIVE_MODEL_ID == "local-model":
            try:
                models = client.models.list()
                if not models.data:
                    error_msg = "System Error: No models are currently loaded in the Bionic Engine. Please load a model (e.g., Llama 3.1 8B) in the LM Studio developer page."
                    try: eel.pushAIMessage(error_msg)
                    except: pass
                    token_queue.put('[DONE]')
                    try: eel.setNovaState('error')
                    except: pass
                    return "ERROR_NO_MODEL"
                ACTIVE_MODEL_ID = models.data[0].id
            except Exception as e:
                log_error(f"Failed to fetch model list from LM Studio: {e}")
                ACTIVE_MODEL_ID = "local-model"

        print_and_log(f"Using model: {ACTIVE_MODEL_ID}")

        # Check if the last message was from the user
        last_user_text = ""
        if len(conversation_history) > 0 and conversation_history[-1]["role"] == "user":
            last_user_text = conversation_history[-1]["content"]

        # 1. Run the Intent Router to see if a tool is needed based on keywords
        # Only route if it's not the hidden boot sequence
        tool_name = None
        if "[SYSTEM_BOOT_SEQUENCE]" not in last_user_text and "The system has just successfully booted up." not in last_user_text:
             tool_name = intent_router(last_user_text)

        # 2. Stage 1 Execution: The Tool Pathway
        if tool_name:
            print_and_log(f"[SYSTEM] Intent Router matched tool: {tool_name}")
            safe_add_activity_log('system', f"Intent Router detected need for tool: {tool_name}")

            # Check Streamer Mode locks
            is_tool_safe = stream_safe_tools.get(tool_name, False)
            if streamer_mode_enabled and not is_tool_safe:
                tool_output = f"SYSTEM ERROR: Execution of {tool_name} is BLOCKED because Streamer Mode is active and this tool is not marked as Stream Safe. Tell the user you cannot perform this action while live."
                print_and_log(f"[SYSTEM] BLOCKED tool {tool_name} due to Streamer Mode.")
                safe_add_activity_log('system', f"Tool {tool_name} BLOCKED by Streamer Mode.")
            else:
                import os
                import json
                import random
                import subprocess

                # Load a processing message to speak while the tool runs
                config_path = os.path.join("tools", tool_name, "config.json")
                if os.path.exists(config_path):
                    try:
                        with open(config_path, "r", encoding="utf-8") as f:
                            config = json.load(f)
                            messages = config.get("processing_messages", [])
                            if messages:
                                holding_msg = random.choice(messages)
                                print_and_log(f"NOVA (Holding): {holding_msg}")
                                # We no longer push this immediately as a new bubble because fast tool executions
                                # cause it to race condition with the main LLM streaming response bubble.
                                # The backend TTS handles it correctly, but visually we just want it integrated.
                                # eel.pushAIMessage handles overlapping automatically now by checking if a stream is active.
                                try: eel.pushAIMessage(f"{holding_msg}")
                                except: pass
                                clean_speech = clean_text_for_speech(holding_msg)
                                if clean_speech:
                                    tts_queue.put(clean_speech)
                    except Exception as e:
                        pass

                # Execute the tool
                # We need to perform a fast, single-tool LLM pass to extract the arguments.
                script_path = os.path.join("tools", tool_name, "main.py")
                schema_path = os.path.join("tools", tool_name, "schema.json")
                tool_output = ""

                if os.path.exists(script_path) and os.path.exists(schema_path):
                    python_exe = sys.executable.replace("pythonw.exe", "python.exe")

                    try:
                        with open(schema_path, "r", encoding="utf-8") as f:
                            tool_schema = json.load(f)
                    except Exception as e:
                        tool_schema = None
                        log_error(f"Failed to load schema for {tool_name}: {e}")

                    if tool_schema:
                        # Fast LLM pass to extract parameters
                        extract_history = list(conversation_history)
                        extract_history.append({
                            "role": "system",
                            "content": f"You must use the '{tool_name}' tool. Output ONLY the raw JSON arguments needed for the tool based on the user's request. DO NOT output any other text."
                        })

                        kwargs_extract = {
                            "model": ACTIVE_MODEL_ID,
                            "messages": extract_history,
                            "temperature": 0.1, # Low temp for strict JSON
                            "tools": [tool_schema],
                            "tool_choice": "auto"
                        }

                        response_extract = client.chat.completions.create(**kwargs_extract)
                        msg = response_extract.choices[0].message

                        tool_args_str = "{}"

                        if msg.tool_calls:
                            tc = msg.tool_calls[0]
                            if tc.function and tc.function.arguments:
                                tool_args_str = tc.function.arguments
                        elif msg.content:
                            # Fallback if it output JSON in content
                            ai_text = msg.content
                            start = ai_text.find('{')
                            end = ai_text.rfind('}')
                            if start != -1 and end != -1 and end > start:
                                json_str = ai_text[start:end+1]
                                try:
                                    tool_data = json.loads(json_str)
                                    target_block = tool_data
                                    if "function" in tool_data and isinstance(tool_data["function"], dict):
                                        target_block = tool_data["function"]
                                    args = target_block.get("arguments") or target_block.get("parameters", target_block)
                                    if isinstance(args, dict):
                                        tool_args_str = json.dumps(args)
                                    else:
                                        tool_args_str = str(args)
                                except:
                                    pass

                        print_and_log(f"[SYSTEM] Extracted args for {tool_name}: {tool_args_str}")

                        # Ensure background tools don't pop up a cmd window on Windows
                        creationflags = 0
                        if os.name == 'nt':
                            creationflags = subprocess.CREATE_NO_WINDOW

                        cmd = [python_exe, script_path, tool_args_str]
                        result = subprocess.run(cmd, capture_output=True, text=True, creationflags=creationflags)
                        tool_output = result.stdout.strip()
                        if result.stderr.strip():
                            tool_output += f"\nError Output: {result.stderr.strip()}"
                    else:
                         tool_output = f"Error: Could not load schema for {tool_name}."

                    vis_output = tool_output
                    if len(vis_output) > 500:
                        vis_output = vis_output[:500] + "... (truncated)"
                    safe_add_activity_log('tool', f"Tool Result:<br><span style='font-size: 10px; color: #0f0;'>{vis_output}</span>")
                else:
                    tool_output = f"Error: Tool {tool_name} not found."
                    safe_add_activity_log('system', f"Error: Tool {tool_name} not found.")

            # Stage 3: Spoon-feed the result to the LLM
            # We replace the user's last message with the spoon-fed prompt.
            spoon_fed_prompt = f"The user asked: {last_user_text}\n\nHere is the system data:\n{tool_output}\n\nReply to the user using ONLY this data. Do not narrate your process. Give a direct conversational answer."

            # Temporarily replace the last history item
            exec_history = list(conversation_history)
            exec_history[-1] = {"role": "user", "content": spoon_fed_prompt}

            kwargs = {
                "model": ACTIVE_MODEL_ID,
                "messages": exec_history,
                "temperature": 0.7,
                "stream": True
            }
            # We DO NOT pass tools_array or tool_choice. The LLM has no tools, it just speaks.

            response = client.chat.completions.create(**kwargs)

        else:
            # Stage 2: Normal LLM Chat (No Tool Needed)
            kwargs = {
                "model": ACTIVE_MODEL_ID,
                "messages": conversation_history,
                "temperature": 0.7,
                "stream": True
            }
            # We DO NOT pass tools. This forces it to just talk and bypasses the 2.5 min tool validation wait.
            response = client.chat.completions.create(**kwargs)

        # Stream the response
        ai_text = ""
        sentence_buffer = ""
        has_started_printing = False
        startup_buffer = ""

        # Iterate over the streamed chunks
        for chunk in response:
            delta = chunk.choices[0].delta

            if delta.content is not None:
                token = delta.content

                # We need to robustly strip out random hallucinations at the very start of the sequence.
                # Sometimes the LLM spits out "s \n\n" or ". r \n\n" before the actual sentence begins.
                if not has_started_printing:
                    startup_buffer += token
                    clean_start = startup_buffer.lstrip(' \n\r\t".,!?;:-')

                    # We wait until the LLM has generated a chunk of text that actually looks like the start
                    # of a real word/sentence (e.g. at least 2 alphanumeric characters long, or a full word).
                    if len(clean_start.strip()) < 2:
                        continue

                    # Now that we have a real word starting, we dump the cleaned buffer and set the flag!
                    token = clean_start
                    has_started_printing = True

                ai_text += token
                sentence_buffer += token
                token_queue.put(token)

                for punc in ['. ', '! ', '? ', '.\n', '!\n', '?\n']:
                    if punc in sentence_buffer:
                        parts = sentence_buffer.split(punc, 1)
                        sentence_to_speak = parts[0] + punc.strip()
                        if sentence_to_speak.strip():
                            clean_speech = clean_text_for_speech(sentence_to_speak)
                            if clean_speech:
                                tts_queue.put(clean_speech)
                        sentence_buffer = parts[1]
                        break

        # Flush any remaining text in the buffer to the TTS queue
        if sentence_buffer.strip():
            clean_speech = clean_text_for_speech(sentence_buffer)
            if clean_speech:
                tts_queue.put(clean_speech)

        # Finished generating.
        print_and_log(f"NOVA: {ai_text}")

        # Update persistent history
        conversation_history.append({
            "role": "assistant",
            "content": ai_text
        })
        save_chat_history()
        token_queue.put('[DONE]')

        try:
            eel.setNovaState('idle')
        except Exception as e:
            log_error(f"Could not update OBS state (is OBS overlay open?): {e}")

    except Exception as e:
        log_error(f"Error during response generation: {e}")
        try: eel.pushAIMessage(f"System Error: I encountered a critical failure. Check nova.log for details.")
        except: pass
        token_queue.put('[DONE]')
        try: eel.setNovaState('error')
        except: pass

@eel.expose
def get_tts_voices():
    """Returns a list of local Piper TTS voices."""
    import download_piper_models
    voice_list = []
    for vid, data in download_piper_models.VOICES.items():
        voice_list.append({"id": vid, "name": data["name"], "desc": data["desc"]})
    return voice_list

current_dsp_prefs = {}

@eel.expose
def set_tts_voice(voice_id):
    """Sets the active voice for the Piper engine via command queue."""
    if voice_id:
        tts_queue.put({"type": "set_voice", "voice_id": voice_id})
        print_and_log(f"Requested TTS Voice change to: {voice_id}")

@eel.expose
def set_tts_params(rate, volume, gap=0.2):
    """Sets the speech rate, volume, and sentence gap for the Piper engine via command queue."""
    tts_queue.put({"type": "set_params", "rate": rate, "volume": volume, "gap": gap})
    print_and_log(f"Requested TTS Params change: Rate={rate}, Volume={volume}, Gap={gap}s")

@eel.expose
def set_dsp_prefs(dsp_prefs):
    """Updates the advanced DSP effects dictionary."""
    global current_dsp_prefs
    current_dsp_prefs = dsp_prefs
    print_and_log(f"Requested DSP Params change: {dsp_prefs}")

@eel.expose
def save_tts_prefs(voice_id, rate, volume, gap=0.2, dsp_prefs=None):
    """Saves TTS and DSP preferences to a config file."""
    prefs = {
        "voice_id": voice_id,
        "rate": rate,
        "volume": volume,
        "gap": gap,
        "dsp_prefs": dsp_prefs or {}
    }
    try:
        with open("tts_config.json", "w") as f:
            json.dump(prefs, f)
        print_and_log("Saved TTS preferences to tts_config.json")
    except Exception as e:
        print_and_log(f"[ERROR] Failed to save TTS prefs: {e}")

@eel.expose
def load_tts_prefs():
    """Loads TTS preferences from a config file."""
    if os.path.exists("tts_config.json"):
        try:
            with open("tts_config.json", "r") as f:
                return json.load(f)
        except Exception as e:
            print_and_log(f"[ERROR] Failed to load TTS prefs: {e}")
    return None

def apply_dsp_effects(audio_data, sample_rate):
    """Applies a chain of advanced DSP effects based on user preferences."""
    global current_dsp_prefs

    # Fast path if DSP is entirely off or empty
    if not current_dsp_prefs or not current_dsp_prefs.get('enabled', False):
        return audio_data

    # Convert to float32 for math
    audio_float = audio_data.astype(np.float32) / 32768.0

    # 1. High-Pass Filter
    hp_freq = current_dsp_prefs.get('hp_freq', 0)
    if hp_freq > 20:
        nyquist = 0.5 * sample_rate
        cutoff = hp_freq / nyquist
        if cutoff < 1.0:
            b, a = signal.butter(4, cutoff, btype='high', analog=False)
            audio_float = signal.filtfilt(b, a, audio_float)

    # 2. Low-Pass Filter
    lp_freq = current_dsp_prefs.get('lp_freq', 20000)
    if lp_freq < 20000:
        nyquist = 0.5 * sample_rate
        cutoff = lp_freq / nyquist
        if cutoff < 1.0:
            b, a = signal.butter(4, cutoff, btype='low', analog=False)
            audio_float = signal.filtfilt(b, a, audio_float)

    # 3. Distortion/Drive
    drive = current_dsp_prefs.get('drive', 0.0)
    if drive > 0.0:
        # Simple soft clipping distortion: out = tanh(in * (1 + drive*10))
        gain = 1.0 + (drive * 10.0)
        audio_float = np.tanh(audio_float * gain)
        # Compensate for volume boost somewhat
        audio_float = audio_float / (1.0 + drive * 0.5)

    # 4. Chorus/Flanger
    chorus_mix = current_dsp_prefs.get('chorus_mix', 0.0)
    if chorus_mix > 0.0:
        chorus_depth = current_dsp_prefs.get('chorus_depth', 0.005) # 5ms base delay
        chorus_rate = current_dsp_prefs.get('chorus_rate', 1.0) # 1 Hz LFO

        # We will do a static delay here for simplicity since true LFO chorus in numpy
        # requires time-varying resampling which is slow and complex.
        # This acts more like a static tight doubler/slapback which still sounds very robotic/metallic.
        delay_samples = int(sample_rate * chorus_depth)
        if delay_samples > 0:
            delayed_audio = np.zeros_like(audio_float)
            delayed_audio[delay_samples:] = audio_float[:-delay_samples]
            audio_float = (audio_float * (1.0 - chorus_mix)) + (delayed_audio * chorus_mix)

    # 5. Delay (Echo)
    delay_mix = current_dsp_prefs.get('delay_mix', 0.0)
    if delay_mix > 0.0:
        delay_time = current_dsp_prefs.get('delay_time', 0.3)
        delay_feedback = current_dsp_prefs.get('delay_feedback', 0.3)

        delay_samples = int(sample_rate * delay_time)
        if delay_samples > 0:
            # We must extend the array to accommodate the delay tail
            tail_length = delay_samples * 3 # Allow a few bounces
            extended_audio = np.pad(audio_float, (0, tail_length), mode='constant')

            wet_signal = np.zeros_like(extended_audio)

            # Simple feedback delay line (only doing a few fixed iterations for performance)
            for i in range(3): # 3 bounces
                bounce = np.zeros_like(extended_audio)
                offset = delay_samples * (i + 1)

                # We need to slice the original audio_float so it fits exactly in the remaining space of bounce
                remaining_space = len(extended_audio) - offset
                if remaining_space > 0:
                    copy_length = min(len(audio_float), remaining_space)
                    bounce[offset:offset+copy_length] = audio_float[:copy_length] * (delay_feedback ** (i+1))
                    wet_signal += bounce

            audio_float = (extended_audio * (1.0 - delay_mix)) + (wet_signal * delay_mix)

    # 6. Reverb
    reverb_mix = current_dsp_prefs.get('reverb_mix', 0.0)
    if reverb_mix > 0.0:
        room_size = current_dsp_prefs.get('reverb_size', 0.3)

        # Create an exponentially decaying impulse response based on room size
        ir_length = int(sample_rate * max(0.1, room_size))
        t = np.linspace(0, 1, ir_length, endpoint=False)
        impulse = np.exp(-10 * t) * np.random.randn(ir_length)

        # Convolve
        reverb = signal.fftconvolve(audio_float, impulse, mode='full')[:len(audio_float)]

        # Normalize reverb tail
        if np.max(np.abs(reverb)) > 0:
            reverb = reverb / np.max(np.abs(reverb))

        audio_float = (audio_float * (1.0 - reverb_mix)) + (reverb * reverb_mix)

    # Normalize back to 16-bit PCM
    final_audio = np.clip(audio_float, -1.0, 1.0)
    return (final_audio * 32767).astype(np.int16)

def tts_worker():
    """
    Background worker that listens for text in the queue and speaks it using piper-tts.
    """
    global tts_active
    import os
    import time
    from piper import PiperVoice
    import numpy as np
    import sounddevice as sd
    import download_piper_models

    # We map WPM (words per minute) to Piper's length_scale.
    # length_scale > 1 is slower, < 1 is faster. Normal is 1.0 (approx ~150 WPM)
    current_worker_voice = "en_GB-alba-medium"
    current_worker_rate = 200 # WPM
    current_worker_volume = 1.0 # 0.0 to 1.0
    current_worker_sentence_gap = 0.2

    piper_model_instance = None
    loaded_voice_id = None

    def load_voice(voice_id):
        nonlocal piper_model_instance, loaded_voice_id
        if voice_id == loaded_voice_id and piper_model_instance is not None:
            return True

        model_path = os.path.join(download_piper_models.MODELS_DIR, f"{voice_id}.onnx")
        if not os.path.exists(model_path):
            print_and_log(f"[TTS WORKER] Downloading model {voice_id} on the fly...")
            success = download_piper_models.download_voice(voice_id)
            if not success:
                return False

        try:
            print_and_log(f"[TTS WORKER] Loading Piper voice: {voice_id} into memory.")
            piper_model_instance = PiperVoice.load(model_path)
            loaded_voice_id = voice_id
            return True
        except Exception as e:
            log_error(f"[TTS WORKER] Failed to load Piper voice {voice_id}: {e}")
            return False

    while True:
        task = tts_queue.get()
        if not task:
            continue

        if isinstance(task, dict):
            if task.get("type") == "set_voice":
                current_worker_voice = task["voice_id"]
                print_and_log(f"Worker cached TTS Voice preference: {current_worker_voice}")
                load_voice(current_worker_voice)
            elif task.get("type") == "set_params":
                if "rate" in task:
                    current_worker_rate = float(task["rate"])
                if "volume" in task:
                    current_worker_volume = float(task["volume"])
                if "gap" in task:
                    current_worker_sentence_gap = float(task["gap"])
                print_and_log(f"Worker cached TTS Params: Rate={current_worker_rate}, Volume={current_worker_volume}, Gap={current_worker_sentence_gap}")
            continue

        text = task
        tts_active = True

        try:
            if not piper_model_instance:
                success = load_voice(current_worker_voice)
                if not success:
                    raise Exception("Failed to load a valid voice model.")

            # Map WPM to length_scale
            # If 150 WPM = 1.0 length scale
            # Then 300 WPM = 0.5 length scale
            base_wpm = 150.0
            length_scale = base_wpm / max(current_worker_rate, 50.0)

            print_and_log(f"[TTS WORKER] Generating audio via piper: {text}")

            # Piper synthesize returns an iterator of audio frames (int16 bytes)
            # We will collect them all into a numpy array so we can apply DSP before playing.
            import piper.config
            syn_config = piper.config.SynthesisConfig(length_scale=length_scale)
            audio_stream = piper_model_instance.synthesize(text, syn_config=syn_config)

            audio_bytes = b""
            for chunk in audio_stream:
                audio_bytes += chunk.audio_int16_bytes

            if audio_bytes:
                # Convert raw PCM16 bytes to numpy array
                audio_data = np.frombuffer(audio_bytes, dtype=np.int16)
                sample_rate = piper_model_instance.config.sample_rate

                # DSP processing will be added here
                # apply_dsp_effects() expects int16, converts to float32 inside, and returns int16
                processed_audio = apply_dsp_effects(audio_data, sample_rate)

                # Apply Volume scaling
                processed_float = processed_audio.astype(np.float32) * current_worker_volume
                processed_audio = np.clip(processed_float, -32768, 32767).astype(np.int16)

                # Append 150ms of pure silence to the end to prevent playback hardware from
                # clamping the audio stream closed before the final phoneme finishes playing
                silence_padding = np.zeros(int(sample_rate * 0.15), dtype=np.int16)
                processed_audio = np.concatenate((processed_audio, silence_padding))

                # Play using sounddevice
                sd.play(processed_audio, samplerate=sample_rate)
                sd.wait() # Block until audio is finished playing

                print_and_log(f"[TTS WORKER] Playback finished for this sentence.")
                time.sleep(current_worker_sentence_gap)
            else:
                log_error("[TTS WORKER] Piper returned no audio bytes.")

        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            log_error(f"[TTS WORKER] CRITICAL ERROR: {error_trace}")
        finally:
            tts_active = False

# Start the TTS worker thread
threading.Thread(target=tts_worker, daemon=True).start()

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
def set_tool_stream_safe(tool_name, is_safe):
    global stream_safe_tools
    stream_safe_tools[tool_name] = is_safe
    print_and_log(f"[SYSTEM] Stream Safe for {tool_name} set to {is_safe}")
    try:
        with open("stream_safe_tools.json", "w") as f:
            json.dump(stream_safe_tools, f)
    except Exception as e:
        print_and_log(f"[ERROR] Failed to save stream safe tools: {e}")

@eel.expose
def open_file_dialog(initial_dir=""):
    """Opens a native OS file dialog and returns the selected path."""
    root = tk.Tk()
    root.withdraw() # Hide the main tk window
    root.attributes('-topmost', True) # Bring to front
    file_path = filedialog.askopenfilename(initialdir=initial_dir, title="Select File")
    root.destroy()
    return file_path

@eel.expose
def get_tool_config(tool_name):
    """Returns the config file for a given tool as a dictionary (or None if none exists)."""
    # Prevent path traversal attacks
    import re
    if not re.match(r'^[\w\-]+$', tool_name):
        log_error(f"Invalid tool_name provided to get_tool_config: {tool_name}")
        return None

    config_path = os.path.join("tools", tool_name, "config.json")
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print_and_log(f"[ERROR] Could not load config for {tool_name}: {e}")
    return None

@eel.expose
def save_tool_config(tool_name, new_config):
    """Saves a JSON dictionary back to the tool's config.json file."""
    # Prevent path traversal attacks
    import re
    if not re.match(r'^[\w\-]+$', tool_name):
        log_error(f"Invalid tool_name provided to save_tool_config: {tool_name}")
        return False

    config_path = os.path.join("tools", tool_name, "config.json")
    try:
        with open(config_path, "w", encoding='utf-8') as f:
            json.dump(new_config, f, indent=4)
        print_and_log(f"[SYSTEM] Saved updated config for {tool_name}.")
        return True
    except Exception as e:
        print_and_log(f"[ERROR] Could not save config for {tool_name}: {e}")
        return False

@eel.expose
def get_stream_safe_tools():
    """Returns the current stream safe locks to the frontend."""
    return stream_safe_tools

@eel.expose
def get_available_tools():
    """Scans the tools/ directory and returns a sorted list of available tool subdirectories."""
    tools_dir = "tools"
    if not os.path.exists(tools_dir):
        return []

    # Get all subdirectories in tools/ that contain a main.py
    available_tools = []
    for item in os.listdir(tools_dir):
        item_path = os.path.join(tools_dir, item)
        if os.path.isdir(item_path) and os.path.isfile(os.path.join(item_path, "main.py")):
            available_tools.append(item)

    available_tools.sort()
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
        global ACTIVE_MODEL_ID
        if not ACTIVE_MODEL_ID or ACTIVE_MODEL_ID == "local-model":
            try:
                models = client.models.list()
                if models.data:
                    ACTIVE_MODEL_ID = models.data[0].id
                else:
                    return
            except Exception as e:
                log_error(f"Presence webhook failed to fetch model: {e}")
                return

        # We append directly to the main conversation history to leverage the existing KV Cache.
        # Sending a one-off temp_history array causes the LLM engine to completely wipe the KV Cache
        # and re-evaluate the entire prompt from scratch, taking minutes to respond.
        conversation_history.append({"role": "user", "content": prompt})

        # Trigger UI to show talking state in OBS
        try: eel.setNovaState('talking')
        except: pass

        tools_array = build_tools_array()
        kwargs = {
            "model": ACTIVE_MODEL_ID,
            "messages": conversation_history,
            "temperature": 0.8
        }
        # ALWAYS pass tools if they exist to keep the prompt prefix identical for KV Caching.
        if tools_array:
            kwargs["tools"] = tools_array
            kwargs["tool_choice"] = "auto" # Do not use "none"

        response = client.chat.completions.create(**kwargs)

        ai_text = response.choices[0].message.content
        print_and_log(f"NOVA (Presence): {ai_text}")

        # Push message directly to the chat UI and history
        conversation_history.append({"role": "assistant", "content": ai_text})

        # We wrap these in separate try/except blocks because Eel broadcasts to all open HTML windows.
        # pushAIMessage exists in index.html but not obs_overlay.html, so it will throw an exception there.
        # We don't want that exception to stop the OBS state from reverting to idle.
        try: eel.pushAIMessage(ai_text)
        except Exception as e: pass

        try: eel.setNovaState('idle')
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
        if self.path == '/stream':
            tokens = []
            while not token_queue.empty():
                tokens.append(token_queue.get())
            self._send_response(200, {"tokens": tokens})
            return

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
                        safe_add_activity_log('system', "Vision system: User absent. Sleep mode activated.")

                    elif event == "wakeup":
                        print_and_log("[PRESENCE API] User returned (Wakeup mode).")
                        time_away = now - presence_state["last_event_time"]

                        if not presence_state["is_present"] or time_away > 120:
                            print_and_log(f"[PRESENCE API] User was away for {int(time_away)}s. Triggering greeting.")
                            safe_add_activity_log('system', "Vision system: User returned. Generating greeting.")
                            threading.Thread(target=generate_presence_message, args=("wakeup",), daemon=True).start()

                        presence_state["is_present"] = True
                        presence_state["last_event_time"] = now
                        presence_state["last_seen"] = now

                    elif event == "leaving":
                        print_and_log("[PRESENCE API] User is actively leaving.")
                        presence_state["is_present"] = False
                        presence_state["last_event_time"] = now
                        safe_add_activity_log('system', "Vision system: User actively leaving. Generating farewell.")
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


def check_single_instance():
    """Ensures only one instance of NOVA runs at a time using a local socket binding."""
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Bind to a completely obscure high port locally
        s.bind(("127.0.0.1", 54320))
        # Keep the socket open and stored in a global so it doesn't garbage collect
        global _lock_socket
        _lock_socket = s
    except socket.error as e:
        print("NOVA is already running! Exiting this instance to prevent conflicts.")
        sys.exit(1)

def start_app():
    # Check for existing instances immediately
    check_single_instance()

    # Load stream safe locks
    global stream_safe_tools
    if os.path.exists("stream_safe_tools.json"):
        try:
            with open("stream_safe_tools.json", "r") as f:
                stream_safe_tools = json.load(f)
        except:
            stream_safe_tools = {}

    # Load phonetic overrides before starting
    load_phonetic_overrides()

    # Initialize TTS worker settings from file if they exist
    prefs = load_tts_prefs()
    if prefs:
        if "effect" in prefs:
            global current_tts_effect
            current_tts_effect = prefs["effect"]
        set_tts_voice(prefs.get("voice_id"))
        set_tts_params(prefs.get("rate", 200), prefs.get("volume", 1.0), prefs.get("gap", 0.2))

    # Start the webhook API in a daemon thread so it dies when the main app closes
    threading.Thread(target=run_presence_server, daemon=True).start()

    # Start the OBS background monitor
    threading.Thread(target=monitor_obs_process, daemon=True).start()

    # Initialize eel pointing to our 'web' folder
    eel.init('web')

    print_and_log("NOVA UI Initialized. Launching window...")
    safe_add_activity_log('system', "NOVA UI Initialized. System Booting...")

    # Start a background health check to verify the LM Studio connection
    def health_check():
        time.sleep(2) # Give the UI a moment to load
        try:
            print_and_log("[SYSTEM] Pinging Bionic Engine...")
            # If this succeeds, it means LM studio is responding
            global ACTIVE_MODEL_ID
            models = client.models.list()
            if models.data:
                ACTIVE_MODEL_ID = models.data[0].id
                try: eel.setSystemStatus('online', 'Bionic Engine Online')
                except: pass
                print_and_log("[SYSTEM] Bionic Engine Online. Triggering boot sequence.")
                try: eel.triggerBootSequence()
                except: pass
            else:
                ACTIVE_MODEL_ID = "local-model"
                try: eel.setSystemStatus('error', 'No Model Loaded')
                except: pass
                print_and_log("[SYSTEM] Connected to LM Studio but no model is loaded.")
        except Exception as e:
            ACTIVE_MODEL_ID = "local-model"
            try: eel.setSystemStatus('error', 'Bionic Engine Offline')
            except: pass
            print_and_log(f"[SYSTEM] Bionic Engine Offline or Unreachable: {e}")

    threading.Thread(target=health_check, daemon=True).start()

    # Start the app. You can tweak geometry here.
    # port=0 forces the OS to pick a random available port, preventing 'Address already in use' errors.
    try:
        eel.start('index.html', size=(900, 700), position=(100, 100), port=0)
    except (SystemExit, KeyboardInterrupt):
        print_and_log("NOVA shut down.")

if __name__ == '__main__':
    start_app()
