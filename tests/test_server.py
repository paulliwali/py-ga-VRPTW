import os
import sys
import threading
import time
import urllib.request
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from server import VRPMVHandler
import socketserver

def test_server_health():
    port = 8899
    socketserver.TCPServer.allow_reuse_address = True
    httpd = socketserver.TCPServer(("", port), VRPMVHandler)
    server_thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    server_thread.start()
    time.sleep(0.1)

    try:
        # Test /health
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/health") as response:
            assert response.status == 200
            content = response.read().decode("utf-8")
            assert "ok" in content

        # Test index.html
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/") as response:
            assert response.status == 200
            html = response.read().decode("utf-8")
            assert "VRPMV" in html
    finally:
        httpd.shutdown()
        httpd.server_close()
