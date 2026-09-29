# The user wants to set up the UI for the Tools.
# Let's outline the plan.
# Plan:
# 1. Modify `get_available_tools()` in `main.py` to also read `config.json` from each tool directory if it exists,
#    and return a structured dictionary containing the tool schemas and any UI configuration parameters they need.
# 2. Add an eel function `save_tool_config(tool_name, config_data)` to save user-inputted keys/IPs to the specific tool's `config.json`.
# 3. Modify `web/index.html` to have a container for dynamic tool configurations in `#tab-tools`.
# 4. Modify `web/main.js` to iterate over the tools provided by `get_available_tools()`, read their parameters,
#    and dynamically build input fields for API keys, IPs, etc. Add a "Save" button to trigger `save_tool_config`.
