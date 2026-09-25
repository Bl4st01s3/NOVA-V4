import json
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

# --- CONFIGURATION ---
# Change this to match the key in NOVA's config.json
API_KEY = "YOUR_SECRET_KEY"
PORT = 5000

# In-memory storage for overnight events
# In a production environment, you might want to save this to a local SQLite DB or JSON file
event_logs = []

class NervousSystemHandler(BaseHTTPRequestHandler):
    def _check_auth(self):
        auth_header = self.headers.get('Authorization')
        if auth_header == f"Bearer {API_KEY}":
            return True
        self._send_response(401, {"error": "Unauthorized. Invalid API Key."})
        return False

    def _send_response(self, status, message):
        self.send_response(status)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(message).encode('utf-8'))

    def do_POST(self):
        """Used by external projects (3D printers, cameras) to log events to the Pi."""
        if not self._check_auth():
            return

        parsed_path = urlparse(self.path)
        if parsed_path.path == '/log':
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length > 0:
                try:
                    post_data = self.rfile.read(content_length)
                    data = json.loads(post_data.decode('utf-8'))

                    # Ensure timestamp exists
                    if "timestamp" not in data:
                        data["timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S")

                    event_logs.append(data)
                    print(f"[LOGGED] {data['timestamp']} - {data.get('source', 'Unknown')}: {data.get('message', '')}")

                    self._send_response(200, {"status": "success", "message": "Event logged successfully."})
                except json.JSONDecodeError:
                    self._send_response(400, {"error": "Invalid JSON payload."})
            else:
                self._send_response(400, {"error": "Missing payload."})
        else:
            self._send_response(404, {"error": "Endpoint not found."})

    def do_GET(self):
        """Used by NOVA to pull the overnight report and clear the cache."""
        global event_logs

        if not self._check_auth():
            return

        parsed_path = urlparse(self.path)
        if parsed_path.path == '/report':
            # Send the logs to NOVA
            response_data = {"events": event_logs}
            self._send_response(200, response_data)

            # Clear the logs so they aren't reported twice
            print(f"[REPORT] Sent {len(event_logs)} events to NOVA. Clearing cache.")
            event_logs = []
        else:
            self._send_response(404, {"error": "Endpoint not found."})

if __name__ == '__main__':
    server = HTTPServer(('0.0.0.0', PORT), NervousSystemHandler)
    print(f"=== NOVA Nervous System Server running on port {PORT} ===")
    print(f"Listening for logs on POST /log")
    print(f"Waiting for NOVA to pull reports on GET /report")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer shutting down.")
        server.server_close()
