import json
import os
import urllib.request
import urllib.error

def run():
    # Load configuration securely without hardcoding IPs
    config_path = os.path.join(os.path.dirname(__file__), "config.json")

    if not os.path.exists(config_path):
        print("Nervous System Error: config.json missing. Cannot connect to Banana Pi.")
        return

    with open(config_path, "r") as f:
        try:
            config = json.load(f)
        except json.JSONDecodeError:
            print("Nervous System Error: Invalid config.json format.")
            return

    pi_ip = config.get("pi_ip")
    pi_port = config.get("pi_port", 5000)
    api_key = config.get("api_key")

    if not pi_ip or not api_key:
        print("Nervous System Error: IP or API Key missing from config.json.")
        return

    url = f"http://{pi_ip}:{pi_port}/report"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {api_key}"})

    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode('utf-8'))
            events = data.get("events", [])

            if not events:
                print("Nervous System (Banana Pi): No new events occurred while you were away.")
            else:
                print("Nervous System (Banana Pi) reported the following overnight/away events:")
                for e in events:
                    t = e.get('timestamp', 'Unknown Time')
                    s = e.get('source', 'Unknown Source')
                    m = e.get('message', '')
                    print(f" - [{t}] {s}: {m}")

    except urllib.error.URLError as e:
        print(f"Nervous System Error: Could not reach Banana Pi at {pi_ip}:{pi_port}. Is the server running? ({e.reason})")
    except Exception as e:
        print(f"Nervous System Error: {str(e)}")

if __name__ == "__main__":
    run()
