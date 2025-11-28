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
from email.utils import parsedate_to_datetime
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
latest_emails = {"inbox": [], "sent": [], "trash": [], "phishing": []}
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


def detect_sent_folder(imap=None):
    if imap is None:
        imap = imaplib.IMAP4(IMAP_HOST, IMAP_PORT)
        imap.login(IMAP_USER, IMAP_PASS)
        close_connection = True
    else:
        close_connection = False
    candidates = ["[Gmail]/Sent Mail", "Sent", "Sent Items", "Sent Messages", "Envoyés", "Gesendet", "Inviati"]
    status, mailboxes = imap.list()
    if status == "OK":
        for mailbox in mailboxes:
            name = mailbox.decode().split('"')[-2] if mailbox else ""
            if any(cand.lower() in name.lower() for cand in candidates):
                if close_connection:
                    imap.logout()
                return name
    if close_connection:
        imap.logout()
    return "Sent"


def detect_trash_folder(imap=None):
    if imap is None:
        imap = imaplib.IMAP4(IMAP_HOST, IMAP_PORT)
        imap.login(IMAP_USER, IMAP_PASS)
        close_connection = True
    else:
        close_connection = False
    candidates = ["[Gmail]/Trash", "Trash", "Deleted Messages", "Bin", "Papierkorb", "Corbeille"]
    status, mailboxes = imap.list()
    if status == "OK":
        for mailbox in mailboxes:
            name = mailbox.decode().split('"')[-2] if mailbox else ""
            if any(cand.lower() in name.lower() for cand in candidates):
                if close_connection:
                    imap.logout()
                return name
    if close_connection:
        imap.logout()
    return "Trash"


def fetch_folder_emails(imap):
    status, data = imap.search(None, "ALL")
    if status != "OK" or not data[0]:
        return []
    email_ids = data[0].split()[-200:]
    emails_list = []
    for num in email_ids:
        if not num:
            continue
        try:
            status, msg_data = imap.fetch(num, "(RFC822)")
            if msg_data == [None]:
                continue
            raw = msg_data[0][1]
            parsed = parse_email(raw)
            emails_list.append(parsed)
        except Exception as e:
            print(f"Failed to fetch message {num}: {e}")
            continue

    def get_timestamp(email_obj):
        date_str = email_obj.get("date", "")
        if not date_str:
            return 0
        try:
            dt = parsedate_to_datetime(date_str)
            return dt.timestamp() if dt else 0
        except:
            return 0

    emails_list.sort(key=get_timestamp, reverse=True)
    return emails_list


def imap_idle_watcher():
    global latest_emails
    while True:
        try:
            imap = imaplib.IMAP4(IMAP_HOST, IMAP_PORT)
            imap.login(IMAP_USER, IMAP_PASS)

            imap.select("INBOX")
            inbox_emails = fetch_folder_emails(imap)

            sent_folder_name = detect_sent_folder(imap)
            imap.select(sent_folder_name)
            sent_emails = fetch_folder_emails(imap)

            trash_folder_name = detect_trash_folder(imap)
            imap.select(trash_folder_name)
            trash_emails = fetch_folder_emails(imap)

            # PHISHING
            try:
                imap.select("Phishing")
                phishing_emails = fetch_folder_emails(imap)
                if phishing_emails != latest_emails["phishing"]:
                    latest_emails["phishing"] = phishing_emails
                    new_mail_event.set()
            except:
                pass  # folder may not exist yet or permission issue

            if trash_emails != latest_emails["trash"]:
                latest_emails["trash"] = trash_emails
                new_mail_event.set()
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
    if folder in ["phishing", "spam"]:
        return jsonify(latest_emails["phishing"])
    return jsonify(latest_emails["inbox"])


@app.route("/send", methods=["POST"])
def send_email():
    try:
        to_addr = request.form.get("to_addr")
        subject = request.form.get("subject")
        body = request.form.get("body")
        if not all([to_addr, subject, body]):
            return "Missing fields", 400

        msg = EmailMessage()
        msg["From"] = IMAP_USER
        msg["To"] = to_addr
        msg["Subject"] = subject
        msg.set_content(body)

        if USE_TLS:
            smtp = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
        else:
            smtp = smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT)
        smtp.login(IMAP_USER, IMAP_PASS)
        smtp.send_message(msg)
        smtp.quit()

        imap = imaplib.IMAP4(IMAP_HOST, IMAP_PORT)
        imap.login(IMAP_USER, IMAP_PASS)
        sent_folder = detect_sent_folder(imap) or "Sent"
        imap.append(sent_folder, None, None, msg.as_bytes())
        imap.logout()

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
        # Start with impossible values so first run always pushes everything
        last_update = {
            "inbox": 0, "sent": 0, "trash": 0,
            "phishing": 0
        }

        while True:
            if new_mail_event.wait(timeout=25):
                for folder in ["inbox", "sent", "trash", "phishing"]:
                    # Force push every single time the watcher ran
                    current_hash = hash(json.dumps(latest_emails[folder], sort_keys=True))
                    if current_hash != last_update[folder]:
                        yield f'event: {folder}\ndata: {json.dumps(latest_emails[folder])}\n\n'
                        last_update[folder] = current_hash
                new_mail_event.clear()
            else:
                yield ": ping\n\n"

    return Response(event_stream(), mimetype="text/event-stream")


def move_or_delete_email(email_id, action="trash"):
    try:
        source_folder = None
        target_email = None
        for folder_key, folder_name in [("inbox", "INBOX"), ("sent", detect_sent_folder)]:
            for e in latest_emails[folder_key]:
                if e["id"] == email_id:
                    source_folder = folder_name() if callable(folder_name) else folder_name
                    target_email = e
                    break
            if target_email:
                break
        if not target_email or not source_folder:
            return False

        dest_folder = detect_trash_folder(None) if action == "trash" else "[Gmail]/All Mail" if "gmail" in IMAP_HOST.lower() else "Archive"

        imap = imaplib.IMAP4(IMAP_HOST, IMAP_PORT)
        imap.login(IMAP_USER, IMAP_PASS)
        imap.select(f'"{source_folder}"')

        subject = target_email["subject"].replace('"', '\\"')
        date_str = parsedate_to_datetime(target_email["date"]).strftime("%d-%b-%Y") if target_email["date"] else ""
        search_query = f'(SUBJECT "{subject}"'
        if date_str:
            search_query += f' SINCE {date_str}'
        search_query += ')'

        status, data = imap.search(None, search_query)
        if status != "OK" or not data[0]:
            status, data = imap.search(None, f'(SUBJECT "{subject}")')

        if status == "OK" and data[0]:
            msg_ids = data[0].split()
            latest_id = msg_ids[-1]
            imap.copy(latest_id, dest_folder)
            imap.store(latest_id, '+FLAGS', '\\Deleted')
            imap.expunge()

        imap.close()
        imap.logout()

        # === INSTANT TRASH UPDATE (THIS IS THE FIX) ===
        if target_email:
            trash_copy = target_email.copy()
            trash_copy["read"] = True
            latest_emails["trash"].insert(0, trash_copy)

            # Force re-sort to trigger SSE even if length didn't change
            latest_emails["trash"].sort(
                key=lambda e: parsedate_to_datetime(e["date"]).timestamp() if e["date"] else 0,
                reverse=True
            )

        # Remove from source
        for folder in ["inbox", "sent"]:
            latest_emails[folder] = [e for e in latest_emails[folder] if e["id"] != email_id]

        new_mail_event.set()  # This now pushes Trash instantly
        return True

    except Exception as e:
        print(f"Move/Delete failed: {e}")
        return False

@app.route("/action", methods=["POST"])
def email_action():
    try:
        data = request.get_json()
        email_id = data.get("id")
        action = data.get("action")
        if not email_id or action not in ["trash", "archive"]:
            return jsonify({"error": "invalid"}), 400

        Thread(target=move_or_delete_email, args=(email_id, action), daemon=True).start()

        # Instant UI remove
        for folder in ["inbox", "sent"]:
            latest_emails[folder] = [e for e in latest_emails[folder] if e["id"] != email_id]
        new_mail_event.set()
        return jsonify({"status": "ok"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    print("PhishAI Webmail — FULLY PERSISTENT + INSTANT TRASH + PERFECT ORDER")
    app.run(host="0.0.0.0", port=1337, debug=False, threaded=True)
