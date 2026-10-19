import sys
import json
import os

def run():
    if len(sys.argv) < 2:
        print("Error: No arguments provided to read_file_aloud tool.")
        return

    try:
        args = json.loads(sys.argv[1])
        file_path = args.get("file_path", "")
        start_line = args.get("start_line")
    except Exception as e:
        print(f"Error parsing arguments: {e}")
        return

    if not file_path:
        print("Error: No file_path provided.")
        return

    if not os.path.exists(file_path):
        print(f"Error: The file '{file_path}' does not exist.")
        return

    if not os.path.isfile(file_path):
        print(f"Error: The path '{file_path}' is not a file.")
        return

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        if start_line and start_line > 0:
            idx = start_line - 1
            if idx < len(lines):
                lines = lines[idx:]
            else:
                print(f"Error: File '{os.path.basename(file_path)}' does not have {start_line} lines.")
                return

        content = "".join(lines)

        # We cap the reading size so it doesn't flood the LLM context or TTS queue infinitely.
        # 5000 characters is a safe limit for a quick readout.
        if len(content) > 5000:
            content = content[:5000] + "\n\n...[Content truncated for length]"

        if not content.strip():
            print(f"The file '{os.path.basename(file_path)}' is empty or has no content after the requested start line.")
            return

        print(f"Content of {os.path.basename(file_path)}:\n\n{content}")

    except UnicodeDecodeError:
        print(f"Error: The file '{file_path}' appears to be a binary file or uses an unsupported encoding.")
    except Exception as e:
        print(f"Error reading file '{file_path}': {e}")

if __name__ == "__main__":
    run()
