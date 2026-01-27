from flask import Flask
from threading import Thread
import os

app = Flask('')

@app.route('/')
def home():
    return "¡Bot encendido y funcionando!"

def run():
    # Render asigna un puerto automáticamente en la variable de entorno PORT
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()