import eel
class DummyEel:
    def expose(self, f): return f
import sys
sys.modules['eel'] = DummyEel()
import main

tools = main.build_tools_array()
import json
print(json.dumps(tools, indent=2))
