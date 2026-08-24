import os
import socket
import threading
import time

import webview

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE_DIR)

URL = "http://127.0.0.1:5000"
ICON = os.path.join(BASE_DIR, "static", "logo.ico")


def server_is_up():
    try:
        with socket.create_connection(("127.0.0.1", 5000), timeout=0.5):
            return True
    except OSError:
        return False


if not server_is_up():
    from app import app

    threading.Thread(
        target=lambda: app.run(debug=False, use_reloader=False),
        daemon=True,
    ).start()

    for _ in range(40):
        if server_is_up():
            break
        time.sleep(0.25)

webview.create_window("VictoLibrary", URL, width=1000, height=800, confirm_close=True)
webview.start(icon=ICON)
