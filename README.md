# NOVA - Personal AI Assistant

NOVA is a personal AI assistant project aiming to provide a Jarvis-like experience running entirely locally on a PC. It serves as a wrapper around the LM Studio "Bionic" LLM engine, providing the power of local LLMs (like Llama 3.1 8B) without cloud dependencies, subscriptions, or privacy concerns.

## Project Goals

* **Local Execution**: Rely on LM Studio's local server rather than external APIs.
* **Futuristic UI**: A cyberpunk-inspired interface using a black background, glowing neon cyan and purple accents, and hexagonal design elements instead of standard rectangles.
* **Multi-modal Interaction**:
  * Phase 1: Text-based chat interface.
  * Phase 2 (Future): Voice integration (local wake word, local STT like Whisper, local TTS) for a truly hands-free assistant experience.
* **Ease of Use**: Simple `.bat` files for setting up the environment and running the application (automatically starting the LLM engine and the UI).
* **Extensibility**: Built in Python to easily integrate future tools and agent capabilities.

## Architecture

This project uses a hybrid architecture to achieve the complex UI requirements while keeping the backend logic in Python:
* **Frontend**: HTML/CSS/JS (for glowing hexagon UI elements).
* **Backend**: Python using a library like `eel` or `pywebview` to bridge the UI with the local LLM logic.
* **Engine**: LM Studio (Bionic) exposing an OpenAI-compatible local server API (usually on `localhost:1234`).

## Setup and Running

1. Run `setup.bat` to install dependencies.
2. Run `run.bat` to launch both the LM Studio background server and the NOVA UI.
