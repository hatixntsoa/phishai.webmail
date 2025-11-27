from flask import Flask, render_template, jsonify, Response, request
import imaplib
import email
from email.policy import default
from threading import Thread, Event
import time
import json
import os
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)

# === Config from .env ===
IMAP_HOST = os.getenv("IMAP_HOST", "localhost")
IMAP_PORT = int(os.getenv("IMAP_PORT", "143"))
IMAP_USER = os.getenv("IMAP_USER")
IMAP_PASS = os.getenv("IMAP_PASS")

SMTP_HOST = os.getenv("SMTP_HOST", "localhost")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
USE_TLS = os.getenv("SMTP_TLS", "true").lower() == "true"

# Global state
latest_emails = { "inbox": [], "sent": [] }
new_mail_event = Event()

def parse_email(raw_msg):
    msg = email.message_from_bytes(raw_msg, policy=default)
    subject = msg["Subject"] or "(no subject)"
    sender = msg["From"] or "Unknown"
    date = msg["Date"] or ""
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                body = part.get_content()
                break
    else:
        body = msg.get_content()
    import re
    sender_name = sender.split("<")[0].strip()
    if not sender_name:
        match = re.search(r'[\w\.-]+@[\w\.-]+', sender)
        sender_name = match.group(0) if match else sender
    return {
        "id": str(int(time.time() * 1000)) + str(hash(subject + body) % 1000),
        "sender": sender_name,
        "subject": subject,
        "body": body,
        "date": date,
        "read": False
    }

def detect_sent_folder(imap):
    candidates = ["[Gmail]/Sent Mail", "Sent", "Sent Items", "Sent Messages", "Envoyés", "Gesendet", "Inviati"]
    status, mailboxes = imap.list()
    if status != "OK": return None
    for mailbox in mailboxes:
        name = mailbox.decode().split('"')[-2] if mailbox else ""
        if any(cand.lower() in name.lower() for cand in candidates):
            return name
    return "Sent"  # fallback

def fetch_folder_emails(imap):
    status, data = imap.search(None, "ALL")
    email_ids = data[0].split()[-200:]  # Last 200 emails
    emails_list = []
    for num in email_ids:
        if not num: continue
        status, msg_data = imap.fetch(num, "(RFC822)")
        if msg_data == [None]: continue
        raw = msg_data[0][1]
        parsed = parse_email(raw)
        emails_list.append(parsed)
    emails_list.reverse()
    return emails_list

def imap_idle_watcher():
    global latest_emails
    while True:
        try:
            imap = imaplib.IMAP4(IMAP_HOST, IMAP_PORT)
            imap.login(IMAP_USER, IMAP_PASS)

            # === INBOX ===
            imap.select("INBOX")
            inbox_emails = fetch_folder_emails(imap)

            # === SENT FOLDER — auto-detect real folder name ===
            sent_folder_name = detect_sent_folder(imap)
            imap.select(sent_folder_name)
            sent_emails = fetch_folder_emails(imap)

            # Update only if changed
            if inbox_emails != latest_emails["inbox"]:
                latest_emails["inbox"] = inbox_emails
                new_mail_event.set()
            if sent_emails != latest_emails["sent"]:
                latest_emails["sent"] = sent_emails
                new_mail_event.set()

            imap.close()
            imap.logout()
            time.sleep(15)

        except Exception as e:
            print(f"IMAP watcher error: {e} — reconnecting in 10s...")
            time.sleep(10)

# Start watcher
Thread(target=imap_idle_watcher, daemon=True).start()
time.sleep(4)

@app.route("/")
def inbox():
    return render_template("index.html", emails=latest_emails["inbox"])

@app.route("/api/emails")
def api_emails():
    folder = request.args.get("folder", "inbox").lower()
    if folder in ["sent", "sent mail", "[gmail]/sent mail", "sent items"]:
        return jsonify(latest_emails["sent"])
    else:
        return jsonify(latest_emails["inbox"])

@app.route("/send", methods=["POST"])
def send_email():
    try:
        to_addr = request.form.get("to_addr")
        subject = request.form.get("subject")
        body = request.form.get("body")
        if not all([to_addr, subject, body]):
            return "Missing fields", 400

        # === Send via SMTP ===
        msg = EmailMessage()
        msg["From"] = IMAP_USER
        msg["To"] = to_addr
        msg["Subject"] = subject
        msg.set_content(body)

        if USE_TLS:
            smtp = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
            # smtp.starttls()
        else:
            smtp = smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT)
        smtp.login(IMAP_USER, IMAP_PASS)
        smtp.send_message(msg)
        smtp.quit()

        # === Save to real Sent folder via IMAP ===
        imap = imaplib.IMAP4(IMAP_HOST, IMAP_PORT)
        imap.login(IMAP_USER, IMAP_PASS)
        sent_folder = detect_sent_folder(imap) or "Sent"
        imap.append(sent_folder, None, None, msg.as_bytes())
        imap.logout()

        # === Add to local cache instantly ===
        sent_email = {
            "id": str(int(time.time() * 1000)),
            "sender": IMAP_USER,
            "subject": subject,
            "body": body,
            "date": time.strftime("%a, %d %b %Y %H:%M:%S %z", time.localtime()),
            "read": True
        }
        latest_emails["sent"].insert(0, sent_email)
        new_mail_event.set()

        return "OK"
    except Exception as e:
        print("Send failed:", e)
        return str(e), 500

@app.route("/stream")
def stream():
    def event_stream():
        last_counts = {"inbox": 0, "sent": 0}
        while True:
            if new_mail_event.wait(timeout=25):
                for folder in ["inbox", "sent"]:
                    current_len = len(latest_emails[folder])
                    if current_len != last_counts[folder]:
                        yield f'event: {folder}\ndata: {json.dumps(latest_emails[folder])}\n\n'
                        last_counts[folder] = current_len
                new_mail_event.clear()
            else:
                yield ": ping\n\n"
    return Response(event_stream(), mimetype="text/event-stream")

if __name__ == "__main__":
    print("PhishAI Webmail — FULLY PERSISTENT SENT FOLDER + REAL-TIME")
    app.run(host="0.0.0.0", port=1337, debug=False, threaded=True)
