import eel
import sys
from openai import OpenAI
import os

# Initialize OpenAI client to connect to local LM Studio server
# Bionic / LM Studio runs an OpenAI-compatible server typically on port 1234
client = OpenAI(base_url="http://localhost:1234/v1", api_key="lm-studio")

# Store conversation history to maintain context
conversation_history = [
    {"role": "system", "content": "You are NOVA, a highly advanced, personal AI assistant. You are concise, helpful, and speak with a futuristic, Jarvis-like tone. You must always reply in plain text. Do not use JSON, do not hallucinate tool calls, and do not format your output as a function call."}
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

        # Call the local LM Studio server
        response = client.chat.completions.create(
            model=model_id,
            messages=conversation_history,
            temperature=0.7,
        )

        # Extract the AI's response
        ai_text = response.choices[0].message.content
        print(f"NOVA: {ai_text}")

        # Append AI response to history
        conversation_history.append({"role": "assistant", "content": ai_text})

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
