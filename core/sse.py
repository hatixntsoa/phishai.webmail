from flask import Response, request
import json
from core.state import latest_emails, new_mail_event

def stream():
    def event_stream():
        last_update = {"inbox": 0, "sent": 0, "trash": 0, "phishing": 0}
        while True:
            if new_mail_event.wait(timeout=25):
                for folder in ["inbox", "sent", "trash", "phishing"]:
                    current_hash = hash(json.dumps(latest_emails[folder], sort_keys=True))
                    if current_hash != last_update[folder]:
                        yield f'event: {folder}\ndata: {json.dumps(latest_emails[folder])}\n\n'
                        last_update[folder] = current_hash
                new_mail_event.clear()
            else:
                yield ": ping\n\n"
    return Response(event_stream(), mimetype="text/event-stream")
