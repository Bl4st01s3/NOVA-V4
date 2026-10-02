import sys
import json
import os

MEMORY_FILE = "long_term_memory.json"

def run():
    if len(sys.argv) < 2:
        print("Error: Memory Manager tool requires parameters.")
        return

    try:
        args = json.loads(sys.argv[1])
        action = args.get("action")
        fact = args.get("fact")

        if not action or not fact:
            print("Error: Missing 'action' or 'fact' in parameters.")
            return

        # Load existing memory
        memory = []
        if os.path.exists(MEMORY_FILE):
            try:
                with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                    memory = json.load(f)
            except Exception:
                memory = []

        if action == "add":
            if fact not in memory:
                memory.append(fact)
                print(f"Memory Manager: Successfully added fact to long-term memory: '{fact}'")
            else:
                print(f"Memory Manager: Fact is already in memory.")
        elif action == "remove":
            if fact in memory:
                memory.remove(fact)
                print(f"Memory Manager: Successfully removed fact from long-term memory: '{fact}'")
            else:
                print(f"Memory Manager: Fact not found in memory.")
        else:
            print(f"Error: Unknown action '{action}'. Use 'add' or 'remove'.")
            return

        # Save memory
        with open(MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump(memory, f, indent=4)

    except Exception as e:
        print(f"Memory Manager Error: {str(e)}")

if __name__ == "__main__":
    run()