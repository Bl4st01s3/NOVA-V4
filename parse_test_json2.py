import json

tool_schema = {
    "type": "function",
    "function": {
        "name": "octoprint",
        "description": "Get the status of the 3D printer.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    }
}

print(json.dumps(tool_schema))
