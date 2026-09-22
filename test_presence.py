import urllib.request
import json

url = "http://127.0.0.1:54321/presence"

def send_event(event):
    data = json.dumps({"event": event}).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req) as response:
            print(f"Sent '{event}': {response.read().decode()}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        send_event(sys.argv[1])
    else:
        print("Usage: python test_presence.py [sleep|wakeup|leaving]")
