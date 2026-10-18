from http.server import BaseHTTPRequestHandler
import sys
class test(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass
print("has log_message")
