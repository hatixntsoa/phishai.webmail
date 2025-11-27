from flask import Flask, render_template, jsonify, Response
import imaplib
import email
from email.policy import default
from threading import Thread, Event
import time
import json
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# === Config from .env ===
IMAP_HOST = os.getenv("IMAP_HOST", "localhost")
IMAP_PORT = int(os.getenv("IMAP_PORT", "143"))
IMAP_USER = os.getenv("IMAP_USER")
IMAP_PASS = os.getenv("IMAP_PASS")

# Global state
latest_emails = []
new_mail_event = Event()  # triggered when new mail arrives
PAGE_SIZE = 25

def parse_email(raw_msg):
    msg = email.message_from_bytes(raw_msg, policy=default)
    subject = msg["Subject"] or "(no subject)"
    sender = msg["From"] or "Unknown"
    date = msg["Date"] or ""

    # Extract plain text body
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                body = part.get_content()
                break
    else:
        body = msg.get_content()

    # Clean sender
    import re
    sender_name = sender.split("<")[0].strip()
    if not sender_name:
        match = re.search(r'[\w\.-]+@[\w\.-]+', sender)
        sender_name = match.group(0) if match else sender

    return {
        "id": str(int(time.time() * 1000)),
        "sender": sender_name,
        "subject": subject,
        "body": body,
        "date": date,
        "read": False
    }


def imap_idle_watcher():
    global latest_emails
    while True:
        try:
            imap = imaplib.IMAP4(IMAP_HOST, IMAP_PORT)
            imap.login(IMAP_USER, IMAP_PASS)
            imap.select("INBOX")

            while True:
                # Fetch latest 20 emails
                status, data = imap.search(None, "ALL")
                email_ids = data[0].split()[-200:]

                new_emails = []
                for num in email_ids:
                    if not num: continue
                    status, msg_data = imap.fetch(num, "(RFC822)")
                    if msg_data == [None]: continue
                    raw = msg_data[0][1]
                    new_emails.append(parse_email(raw))
                new_emails.reverse()  # newest first

                # THIS IS THE KEY: actually update the global list!
                if len(new_emails) != len(latest_emails) or \
                   any(a["id"] != b["id"] for a, b in zip(new_emails, latest_emails)):
                    latest_emails = new_emails
                    new_mail_event.set()  # wake up SSE

                # === CLEAN IDLE (no more errors) ===
                imap.send(b"IDLE\r\n")
                line = imap._get_line()
                if b"OK" not in line:
                    break

                while True:
                    line = imap._get_line().strip()
                    if b"EXISTS" in line or b"RECENT" in line:
                        break
                    if b"Still here" in line:
                        continue
                    if not line:
                        break

                imap.send(b"DONE\r\n")
                imap._get_line()  # consume OK

        except Exception as e:
            print(f"IMAP disconnected: {e} — reconnecting...")
            time.sleep(5)

# Start background watcher
Thread(target=imap_idle_watcher, daemon=True).start()
time.sleep(2)  # give it time to connect

@app.route("/")
def inbox():
    return render_template("index.html", emails=latest_emails)

@app.route("/api/emails")
def api_emails():
    return jsonify(latest_emails)


@app.route("/stream")
def stream():
    def event_stream():
        last_sent = None
        while True:
            if new_mail_event.wait(timeout=25):
                yield f"data: {json.dumps(latest_emails)}\n\n"
                new_mail_event.clear()
                last_sent = len(latest_emails)
            else:
                yield ": ping\n\n"
            # Safety: if count changed without event
            if last_sent != len(latest_emails):
                yield f"data: {json.dumps(latest_emails)}\n\n"
                last_sent = len(latest_emails)
    return Response(event_stream(), mimetype="text/event-stream")


if __name__ == "__main__":
    print("PhishAI Webmail started — real-time with IMAP IDLE + SSE")
    app.run(host="0.0.0.0", port=1337, debug=False, threaded=True)
