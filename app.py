from flask import Flask
import time

from client.imap_worker import *
from routes.inbox import inbox_bp
from routes.actions import actions_bp
from core.sse import stream

app = Flask(__name__)

app.register_blueprint(inbox_bp)
app.register_blueprint(actions_bp)

@app.route("/stream")
def sse_stream():
    return stream()

if __name__ == "__main__":
    print("PhishAI Webmail")
    time.sleep(2)
    app.run(host="0.0.0.0", port=1337, debug=False, threaded=True)
