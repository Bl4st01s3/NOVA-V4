import sys
import os
import json
import urllib.request
import urllib.error

def run():
    config_path = os.path.join(os.path.dirname(__file__), "config.json")

    if not os.path.exists(config_path):
        print("Octoprint Error: config.json missing. Cannot connect to printer.")
        return

    with open(config_path, "r", encoding="utf-8") as f:
        try:
            config = json.load(f)
        except json.JSONDecodeError:
            print("Octoprint Error: Invalid config.json format.")
            return

    settings = config.get("settings", {})
    printer_ip = settings.get("printer_ip", {}).get("value")
    api_key = settings.get("api_key", {}).get("value")

    if not printer_ip or not api_key:
        print("Octoprint Error: IP Address or API Key missing. Please configure them in the Tools Settings.")
        return

    url = f"http://{printer_ip}/api/job"
    req = urllib.request.Request(url, headers={"X-Api-Key": api_key})

    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode('utf-8'))
            state = data.get("state", "Unknown")
            job = data.get("job", {})
            file_name = job.get("file", {}).get("name", "Nothing")
            progress = data.get("progress", {})
            completion = progress.get("completion", 0)

            if completion is None:
                completion = 0

            if state.lower() == "printing":
                print(f"Octoprint Status: Currently printing {file_name}. It is {completion:.1f}% complete.")
            elif state.lower() == "operational":
                print("Octoprint Status: The printer is currently operational and idle.")
            else:
                print(f"Octoprint Status: The printer is in state: {state}.")

    except urllib.error.URLError as e:
        print(f"Octoprint Error: Could not reach Octoprint at {printer_ip}. ({e.reason})")
    except Exception as e:
        print(f"Octoprint Error: {str(e)}")

if __name__ == "__main__":
    run()
