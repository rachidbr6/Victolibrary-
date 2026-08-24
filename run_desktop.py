import threading
import webview
import tkinter as tk
from PIL import Image, ImageTk
from app import app
import os


app.config['DEBUG'] = True


def start_server():
    app.run(debug=True, use_reloader=False)

if __name__ == "__main__":

    # Lancer Flask en thread
    server = threading.Thread(target=start_server)
    server.daemon = True
    server.start()

    # Chemin du fichier ICO pour PyWebView
    icon_path = os.path.join("static", "logo.ico")

    # Créer la fenêtre PyWebView
    webview.create_window(
        "VictoLibrary",
        "http://127.0.0.1:5000",
        width=1000,
        height=800,
        confirm_close=True,
    
    )

    webview.start()
