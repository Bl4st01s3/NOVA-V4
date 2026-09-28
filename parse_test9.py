import json
import main

tools = main.build_tools_array()
print(json.dumps(tools, indent=2))
