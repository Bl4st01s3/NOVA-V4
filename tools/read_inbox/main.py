import sys
import json
import os

def run():
    if len(sys.argv) < 2:
        print("Error: No arguments provided.")
        return

    try:
        args = json.loads(sys.argv[1])
        action = args.get("action", "list_files")
        filename = args.get("filename", "")
    except:
        action = "list_files"
        filename = ""

    # Locate the Desktop folder
    desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
    inbox_path = os.path.join(desktop_path, "NOVA_Inbox")

    # Create the inbox if it doesn't exist so the user has it ready
    if not os.path.exists(inbox_path):
        try:
            os.makedirs(inbox_path)
            print("The NOVA_Inbox folder did not exist on the Desktop, so I have created it. It is currently empty.")
            return
        except Exception as e:
            print(f"Failed to create inbox folder: {e}")
            return

    if action == "list_files":
        try:
            files = os.listdir(inbox_path)
            if not files:
                print("The NOVA_Inbox folder on the Desktop is currently empty.")
            else:
                file_list = "\n".join(files)
                print(f"Files currently in NOVA_Inbox:\n{file_list}")
        except Exception as e:
            print(f"Failed to list files: {e}")

    elif action == "read_file":
        if not filename:
            print("Error: 'filename' must be provided when action is 'read_file'.")
            return

        file_path = os.path.join(inbox_path, filename)

        # Path traversal protection
        if not os.path.abspath(file_path).startswith(os.path.abspath(inbox_path)):
            print("Error: Access denied. Cannot read files outside the inbox.")
            return

        if not os.path.exists(file_path):
            print(f"Error: The file '{filename}' was not found in the inbox.")
            return

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            if len(content) > 5000:
                content = content[:5000] + "\n\n...[Content truncated for length]"

            if not content.strip():
                print(f"The file '{filename}' is empty.")
                return

            print(f"Content of {filename}:\n\n{content}")
        except UnicodeDecodeError:
            print(f"Error: '{filename}' appears to be a binary file or unsupported format.")
        except Exception as e:
            print(f"Failed to read file: {e}")

if __name__ == "__main__":
    run()
