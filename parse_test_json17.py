# The plan to build the Tools UI:
# 1. Modify `get_available_tools()` in `main.py` to only return `available_tools = ["weather", "octoprint", "nervous_system", "calendar"]` as it does currently.
# 2. Add an eel function `get_tool_config(tool_name)` that returns the JSON dictionary from `tools/{tool_name}/config.json`.
# 3. Add an eel function `save_tool_config(tool_name, settings)` that writes the modified `settings` dictionary back into `tools/{tool_name}/config.json`.
# 4. Modify `build_tools_array()` to read `config.json` for each tool and extract the `schema` object, replacing the hardcoded schema strings.
# 5. In `web/main.js`, add `async function loadToolsUI()` that iterates over `availableTools`, fetches their configs using `get_tool_config`,
#    and renders the `settings` keys as inputs in the `#tab-tools .settings-content` div.
