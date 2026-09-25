# NOVA Nervous System (Banana Pi Server)

The "Nervous System" is a lightweight, always-on server designed to run on a secondary device (like a Banana Pi F3 or Raspberry Pi).

Its purpose is to act as a centralized data aggregator. When your main PC (and NOVA) is turned off overnight, your other projects (smart cameras, 3D printers, home automation scripts) can ping this Pi server to log events.

When you sit down at your desk the next morning and NOVA wakes up, she will automatically query the Pi, pull down the overnight event logs, clear the Pi's cache, and brief you on everything that happened while you were away!

## 1. Setting up the Banana Pi

1. Copy the entire `nervous_system_server/` folder from this repository to your Banana Pi.
2. Open `nervous_system_server/server.py` in a text editor and change the `API_KEY` variable to a secure password of your choosing.
3. Run the server using Python 3:
   ```bash
   python3 server.py
   ```
   *(We recommend setting this script to run automatically on boot using `systemd` or `pm2` so it runs 24/7 in the background).*

## 2. Configuring NOVA

To allow NOVA to pull data from the Pi, you need to configure her tool:

1. Open `tools/nervous_system/config.json`.
2. Enter the IP address of your Banana Pi on your local network.
3. Enter the exact same `API_KEY` you set in Step 1.
4. Save the file.
5. In the NOVA UI Settings tab, ensure "Include Nervous_system Data" is checked in the Dynamic Briefing Configuration.

## 3. Pushing Data from Other Projects (e.g. Cybermouse)

Whenever an event happens in one of your other Python projects, simply send an HTTP POST request to the Pi's `/log` endpoint.

**Python Example:**

```python
import urllib.request
import json

# The IP of your Banana Pi
PI_URL = "http://192.168.1.100:5000/log"
API_KEY = "YOUR_SECRET_KEY"

payload = {
    "source": "Cybermouse Vision",
    "message": "Detected unknown movement near the 3D printer."
}

data = json.dumps(payload).encode("utf-8")
req = urllib.request.Request(PI_URL, data=data, headers={
    "Content-Type": "application/json",
    "Authorization": f"Bearer {API_KEY}"
})

try:
    with urllib.request.urlopen(req) as response:
        print("Successfully logged event to NOVA Nervous System.")
except Exception as e:
    print(f"Failed to log event: {e}")
```

The next time you trigger a Presence Wakeup in NOVA, she will read out: *"Nervous System (Banana Pi) reported the following overnight events: Cybermouse Vision detected unknown movement near the 3D printer."*
