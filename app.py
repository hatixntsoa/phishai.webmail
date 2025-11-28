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
latest_emails["trash"] = []
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

def detect_trash_folder(imap):
    candidates = ["[Gmail]/Trash", "Trash", "Deleted Messages", "Bin", "Papierkorb", "Corbeille"]
    status, mailboxes = imap.list()
    if status != "OK": return "Trash"
    for mailbox in mailboxes:
        name = mailbox.decode().split('"')[-2] if mailbox else ""
        if any(cand.lower() in name.lower() for cand in candidates):
            return name
    return "Trash"

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

            # === TRASH (new) ===
            trash_folder_name = detect_trash_folder(imap)
            imap.select(trash_folder_name)
            trash_emails = fetch_folder_emails(imap)
            if trash_emails != latest_emails["trash"]:
                latest_emails["trash"] = trash_emails
                new_mail_event.set()

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
    if folder in ["trash", "bin", "deleted", "[gmail]/trash"]:
        return jsonify(latest_emails["trash"])
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


# === ADDED: Move email to Trash or Archive (real IMAP + instant UI update) ===
def get_source_folder(email_id):
    for folder in ["inbox", "sent"]:
        if any(e["id"] == email_id for e in latest_emails[folder]):
            return "INBOX" if folder == "inbox" else detect_sent_folder(None)
    return "INBOX"

def move_or_delete_email(email_id, action="trash"):
    try:
        source_folder = get_source_folder(email_id)
        dest_folder = "[Gmail]/Trash" if action == "trash" and "gmail" in IMAP_HOST.lower() else "Trash"
        if action == "archive":
            dest_folder = "[Gmail]/All Mail" if "gmail" in IMAP_HOST.lower() else "Archive"

        imap = imaplib.IMAP4(IMAP_HOST, IMAP_PORT)
        imap.login(IMAP_USER, IMAP_PASS)
        imap.select(f'"{source_folder}"' if " " in source_folder else source_folder)

        target_email = None
        for folder in ["inbox", "sent"]:
            for e in latest_emails[folder]:
                if e["id"] == email_id:
                    target_email = e
                    break
            if target_email: break
        if not target_email: return False

        search_query = f'(SUBJECT "{target_email["subject"]}")'
        status, data = imap.search(None, search_query)
        if status != "OK" or not data[0]: return False
        msg_id = data[0].split()[-1]
        if not msg_id: return False

        # THIS IS THE ONLY CHANGE — use MOVE command instead of copy + expunge
        imap.move(msg_id, dest_folder)        # ← correct IMAP MOVE (keeps it in Trash)

        imap.close()
        imap.logout()

        # Remove from local cache (so UI updates instantly)
        for folder in ["inbox", "sent"]:
            latest_emails[folder] = [e for e in latest_emails[folder] if e["id"] != email_id]
        latest_emails["trash"] = []  # force refresh on next view
        new_mail_event.set()
        return True
    except Exception as e:
        print(f"Move/Delete failed: {e}")
        return False

@app.route("/action", methods=["POST"])
def email_action():
    try:
        data = request.get_json()
        email_id = data.get("id")
        action = data.get("action")  # "trash" or "archive"

        if not email_id or action not in ["trash", "archive"]:
            return jsonify({"error": "invalid"}), 400

        # Fire and forget — background move
        Thread(target=move_or_delete_email, args=(email_id, action), daemon=True).start()

        # Instantly remove from UI
        for folder in ["inbox", "sent"]:
            latest_emails[folder] = [e for e in latest_emails[folder] if e["id"] != email_id]
        new_mail_event.set()

        return jsonify({"status": "ok"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500



if __name__ == "__main__":
    print("PhishAI Webmail — FULLY PERSISTENT SENT FOLDER + REAL-TIME")
    app.run(host="0.0.0.0", port=1337, debug=False, threaded=True)
