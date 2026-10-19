import sys
import json
import os

# When executed by main.py, the cwd is the project root.
DROPBOX_REGISTRY = os.path.join("dropbox", "registry.json")

def run():
    if len(sys.argv) < 2:
        print("Error: No arguments provided.")
        return

    try:
        args = json.loads(sys.argv[1])
        action = args.get("action", "list_files")
        filename = args.get("filename", "")
        start_line = args.get("start_line")
    except:
        action = "list_files"
        filename = ""
        start_line = None

    if not os.path.exists(DROPBOX_REGISTRY):
        print("The Drop Box is currently empty.")
        return

    try:
        with open(DROPBOX_REGISTRY, "r", encoding="utf-8") as f:
            registry = json.load(f)
    except Exception as e:
        print(f"Error reading Drop Box registry: {e}")
        return

    if action == "list_files":
        if not registry:
            print("The Drop Box is currently empty.")
        else:
            file_list = "\n".join(registry.keys())
            print(f"Files currently in the Drop Box:\n{file_list}")

    elif action == "read_file":
        if not filename:
            print("Error: 'filename' must be provided when action is 'read_file'.")
            return

        file_path = registry.get(filename)

        if not file_path or not os.path.exists(file_path):
            print(f"Error: The file '{filename}' was not found in the Drop Box registry or no longer exists on disk.")
            return

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            if start_line and start_line > 0:
                # 1-indexed to 0-indexed
                idx = start_line - 1
                if idx < len(lines):
                    lines = lines[idx:]
                else:
                    print(f"Error: File '{filename}' does not have {start_line} lines.")
                    return

            content = "".join(lines)

            if len(content) > 5000:
                content = content[:5000] + "\n\n...[Content truncated for length]"

            if not content.strip():
                print(f"The file '{filename}' is empty or has no content after the requested start line.")
                return

            print(f"Content of {filename}:\n\n{content}")
        except UnicodeDecodeError:
            print(f"Error: '{filename}' appears to be a binary file or unsupported format.")
        except Exception as e:
            print(f"Failed to read file: {e}")

if __name__ == "__main__":
    run()
