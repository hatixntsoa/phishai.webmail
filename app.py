from flask import Flask

import threading
import uvicorn
import time

from client.imap_worker import *
from routes.inbox import inbox_bp
from routes.actions import actions_bp
from core.sse import stream

from api.predictor import app as fastapi_app

app = Flask(__name__, template_folder='templates', static_folder='static')
app.register_blueprint(inbox_bp)
app.register_blueprint(actions_bp)


def run_fastapi():
    print("Starting FastAPI predictor API on http://0.0.0.0:8000 ...")
    uvicorn.run(fastapi_app, host="0.0.0.0", port=8000, log_level="error")


@app.route("/stream")
def sse_stream():
    return stream()

if __name__ == "__main__":
    threading.Thread(target=run_fastapi, daemon=True).start()
    time.sleep(2)

    print("PhishAI Webmail")
    app.run(host='0.0.0.0', port=1337, debug=False, use_reloader=False)

    # app.run(host="0.0.0.0", port=1337, debug=False, threaded=True)
