import eel
import sys
from openai import OpenAI
import os

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

    # Append user message to history
    conversation_history.append({"role": "user", "content": user_text})

    try:
        # Fetch available models to auto-select the loaded one
        models = client.models.list()

        if not models.data:
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
            ai_text = message.content
            conversation_history.append({"role": "assistant", "content": ai_text})

        print(f"NOVA: {ai_text}")
        return ai_text

    except Exception as e:
        print(f"Error communicating with LM Studio: {e}")
        return f"System Error: Unable to connect to the Bionic Engine. Please ensure LM Studio server is running on localhost:1234. Details: {str(e)}"

def start_app():
    # Initialize eel pointing to our 'web' folder
    eel.init('web')

    print("NOVA UI Initialized. Launching window...")

    # Start the app. You can tweak geometry here.
    try:
        eel.start('index.html', size=(900, 700), position=(100, 100))
    except (SystemExit, KeyboardInterrupt):
        print("NOVA shut down.")

if __name__ == '__main__':
    start_app()
