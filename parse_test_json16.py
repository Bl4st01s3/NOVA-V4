# The user wants to set up the Tools Configuration tab so they can input Octoprint IPs and nervous system API keys.
# Let's create standard config.json structures for the tools.
# Let's look at what Nervous System uses:
# { "pi_ip": "...", "pi_port": 5000, "api_key": "..." }
# Let's look at Octoprint. What would Octoprint use?
# { "printer_ip": "...", "api_key": "..." }
#
# But the LLM schema (the description of the tool given to Llama 3) shouldn't be hardcoded in `main.py` anymore!
# Each tool's `config.json` should probably define its LLM schema so `main.py` is fully modular!
