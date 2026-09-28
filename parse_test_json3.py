import json

tool_schema = {
    "type": "function",
    "function": {
        "name": "octoprint",
        "description": "Get the status of the 3D printer."
    }
}
print(json.dumps(tool_schema))
