from core.state import latest_emails, new_mail_event
from flask import Response
from threading import Lock
from queue import Queue
import json

message_queue = Queue()
queue_lock = Lock()

def broadcast(event_name: str, data: str):
    """Send a custom SSE event to all connected clients immediately"""
    with queue_lock:
        message_queue.put((event_name, data))


def stream():
    def event_stream():
        last_update = {"inbox": 0, "sent": 0, "trash": 0, "phishing": 0}
        client_queue = Queue()

        with queue_lock:
            message_queue.put(("__register", client_queue))

        try:
            while True:
                if new_mail_event.wait(timeout=5):
                    for folder in ["inbox", "sent", "trash", "phishing"]:
                        current_hash = hash(json.dumps(latest_emails[folder], sort_keys=True))
                        if current_hash != last_update[folder]:
                            yield f'event: {folder}\ndata: {json.dumps(latest_emails[folder])}\n\n'
                            last_update[folder] = current_hash
                    new_mail_event.clear()

                try:
                    while True:
                        event_name, payload = message_queue.get_nowait()
                        if event_name == "__register":
                            continue
                        elif event_name == "__unregister":
                            continue
                        else:
                            yield f'event: {event_name}\ndata: {payload}\n\n'
                except:
                    pass

                yield ": heartbeat\n\n"

        finally:
            with queue_lock:
                message_queue.put(("__unregister", client_queue))

    return Response(event_stream(), mimetype="text/event-stream")
