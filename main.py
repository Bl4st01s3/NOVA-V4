import eel
import sys
from openai import OpenAI
import os
import threading
import json
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from datetime import datetime

# Initialize OpenAI client to connect to local LM Studio server
# Bionic / LM Studio runs an OpenAI-compatible server typically on port 1234
client = OpenAI(base_url="http://localhost:1234/v1", api_key="lm-studio")

# Default prompt in case the file gets deleted
DEFAULT_SYSTEM_PROMPT = """You are NOVA, a highly advanced, personal AI assistant.
You are concise, helpful, and speak with a futuristic, Jarvis-like tone.
You must always reply in plain text. Do not use JSON, do not hallucinate tool calls, and do not format your output as a function call."""

# Load system prompt from file so it's easily editable by the user
def load_system_prompt():
    prompt_file = "system_prompt.txt"
    if os.path.exists(prompt_file):
        with open(prompt_file, "r", encoding="utf-8") as f:
            return f.read().strip()
    else:
        # Create the file with the default prompt if it doesn't exist
        with open(prompt_file, "w", encoding="utf-8") as f:
            f.write(DEFAULT_SYSTEM_PROMPT)
        return DEFAULT_SYSTEM_PROMPT

# Store conversation history to maintain context
conversation_history = [
    {"role": "system", "content": load_system_prompt()}
]

@eel.expose
def send_message_to_nova(user_text):
    """
    Called from JS when the user sends a message.
    """
    print(f"User: {user_text}")

    # Notify OBS Overlay that we are processing/talking
    try:
        eel.setNovaState('talking')()
    except Exception as e:
        print(f"Info: Could not update OBS state (is OBS overlay open?): {e}")

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
        print(f"Using model: {model_id}")

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

        # Call the local LM Studio server
        response = client.chat.completions.create(
            model=model_id,
            messages=conversation_history,
            temperature=0.7,
            tools=tools,
            tool_choice="auto" # Let the model decide to use tools
        )

        message = response.choices[0].message

        ai_text = ""

        # Check if the AI decided to call a tool
        if message.tool_calls:
            for tool_call in message.tool_calls:
                eel.addActivityLog('tool', f"LLM decided to call tool: <b>{tool_call.function.name}</b>")
                if tool_call.function.name == "speak":
                    import json
                    try:
                        args = json.loads(tool_call.function.arguments)
                        ai_text = args.get("text", "")
                    except json.JSONDecodeError:
                        ai_text = "Error: Failed to parse speech output."

            # For the history to be continuous in OpenAI format, we technically need to append the tool call
            # and then append a 'tool' role response. Since we are just extracting text for the UI right now,
            # we will store the extracted text directly as the assistant response so it remembers the conversation natively.
            conversation_history.append({"role": "assistant", "content": ai_text})

        # Handle case where AI responds with standard text instead of a tool
        elif message.content:
            eel.addActivityLog('system', "LLM responded with standard text instead of using a tool.")
            ai_text = message.content
            conversation_history.append({"role": "assistant", "content": ai_text})

        print(f"NOVA: {ai_text}")

        # Revert OBS to idle when done talking
        try: eel.setNovaState('idle')()
        except: pass

        return ai_text

    except Exception as e:
        print(f"Error communicating with LM Studio: {e}")
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

briefing_prefs = {
    "weather": True,
    "printer": True,
    "calendar": False
}

@eel.expose
def update_briefing_prefs(prefs):
    global briefing_prefs
    briefing_prefs.update(prefs)
    print(f"Updated Briefing Preferences: {briefing_prefs}")

def generate_presence_message(event_type):
    """
    Called when a wakeup event occurs after being away, or a manual leave event occurs.
    It prompts the LLM for a quick, dynamic JARVIS-like greeting/farewell based on time.
    """
    now = datetime.now()
    current_time_str = now.strftime("%I:%M %p")

    if event_type == "wakeup":
        prompt = f"The user has just returned to their desk. The current time is {current_time_str}. Give a short, futuristic, JARVIS-like greeting to welcome them back."

        # Add dynamic briefing elements based on preferences
        brief_elements = []
        if briefing_prefs.get("weather"):
            brief_elements.append("the current local weather (you can hallucinate placeholder data like 'raining and 6 Degrees Celsius' for now to demonstrate the capability)")
        if briefing_prefs.get("printer"):
            brief_elements.append("the status of the 2.4 3D printer (you can hallucinate placeholder data like 'finished its print at 6:47am, bed is 42C, ready to be removed' to demonstrate the capability)")
        if briefing_prefs.get("calendar"):
            brief_elements.append("a quick summary of today's schedule (hallucinate 1 or 2 placeholder events)")

        if brief_elements:
            prompt += " As part of your greeting, include a quick briefing report containing: " + ", ".join(brief_elements) + "."
            prompt += " Format it smoothly and ask if they need anything else."

        prompt += " Do not use tools, just return the plain text greeting."

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
        print(f"NOVA (Presence): {ai_text}")

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
        print(f"Failed to generate presence message: {e}")


class PresenceRequestHandler(BaseHTTPRequestHandler):
    def _send_response(self, status, message):
        self.send_response(status)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(message).encode('utf-8'))

    def do_POST(self):
        if self.path == '/presence':
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length > 0:
                post_data = self.rfile.read(content_length)
                try:
                    data = json.loads(post_data.decode('utf-8'))
                    event = data.get('event')
                    now = time.time()

                    if event == "sleep":
                        print("\n[PRESENCE API] User has gone idle/left (Sleep mode).")
                        presence_state["is_present"] = False
                        presence_state["last_event_time"] = now
                        try: eel.addActivityLog('system', "Vision system: User absent. Sleep mode activated.")()
                        except: pass

                    elif event == "wakeup":
                        print("\n[PRESENCE API] User returned (Wakeup mode).")
                        time_away = now - presence_state["last_event_time"]

                        if not presence_state["is_present"] or time_away > 120:
                            print(f"[PRESENCE API] User was away for {int(time_away)}s. Triggering greeting.")
                            try: eel.addActivityLog('system', "Vision system: User returned. Generating greeting.")()
                            except: pass
                            threading.Thread(target=generate_presence_message, args=("wakeup",), daemon=True).start()

                        presence_state["is_present"] = True
                        presence_state["last_event_time"] = now
                        presence_state["last_seen"] = now

                    elif event == "leaving":
                        print("\n[PRESENCE API] User is actively leaving.")
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
    print(f"Starting local webhook presence API on http://127.0.0.1:{port}/presence")
    server.serve_forever()


def start_app():
    # Start the webhook API in a daemon thread so it dies when the main app closes
    threading.Thread(target=run_presence_server, daemon=True).start()

    # Initialize eel pointing to our 'web' folder
    eel.init('web')

    print("NOVA UI Initialized. Launching window...")

    # Start the app. You can tweak geometry here.
    # port=0 forces the OS to pick a random available port, preventing 'Address already in use' errors.
    try:
        eel.start('index.html', size=(900, 700), position=(100, 100), port=0)
    except (SystemExit, KeyboardInterrupt):
        print("NOVA shut down.")

if __name__ == '__main__':
    start_app()
