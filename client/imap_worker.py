from utils.helpers import detect_sent_folder, detect_trash_folder
from core.state import latest_emails, new_mail_event
from client.parser import parse_email, get_timestamp
from client.actions import move_msg

from threading import Thread
import requests
import imaplib
import time
import re

from config import IMAP_HOST, IMAP_PORT, IMAP_USER, IMAP_PASS, MODEL_API

def safe_decode(x):
    if isinstance(x, bytes):
        return x.decode('utf-8', errors='ignore')
    return str(x)


def batch_predict(emails_batch):
    if not emails_batch:
        return []

    try:
        print("Asking PhishAI")
        print("Let him cook")
        response = requests.post(
            MODEL_API,
            json={"emails": emails_batch},
            # timeout=60
        )
        if response.status_code == 200:
            return response.json().get("verdicts", [])
        else:
            print(f"API error {response.status_code}: {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"Failed to reach model API: {e}")

    return []

def fetch_folder_emails(imap, folder=None):
    if folder:
        imap.select(folder, readonly=True)
    status, data = imap.uid('SEARCH', None, "ALL")
    if status != "OK" or not data[0]:
        return []
    email_ids = data[0].split()[-200:]
    emails = []
    for num in email_ids:
        try:
            status, msg_data = imap.uid('FETCH', num, "(RFC822 FLAGS)")
            if msg_data == [None] or not msg_data[0]:
                continue
            raw = msg_data[0][1]
            parsed = parse_email(raw)
            parsed["uid"] = safe_decode(num)
            emails.append(parsed)
        except:
            continue
    emails.sort(key=get_timestamp, reverse=True)
    return emails


# Create Phishing folder if missing
def ensure_phishing_folder():
    try:
        imap = imaplib.IMAP4(IMAP_HOST, IMAP_PORT)
        imap.login(IMAP_USER, IMAP_PASS)
        imap.create('"Phishing"')
        imap.logout()
        print("Created folder: Phishing")
    except:
        pass


ensure_phishing_folder()


print("Running initial IMAP sync...")
imap = imaplib.IMAP4(IMAP_HOST, IMAP_PORT)
imap.login(IMAP_USER, IMAP_PASS)
imap.select("INBOX")

latest_emails["inbox"] = fetch_folder_emails(imap, "INBOX")

sent_folder = detect_sent_folder(imap)
trash_folder = detect_trash_folder(imap)

latest_emails["sent"] = fetch_folder_emails(imap, sent_folder)
latest_emails["trash"] = fetch_folder_emails(imap, trash_folder)
latest_emails["phishing"] = fetch_folder_emails(imap, "Phishing")

imap.logout()
new_mail_event.set()
print("Initial sync complete — inbox ready!")


def imap_polling_watcher():
    while True:
        imap = None
        try:
            imap = imaplib.IMAP4(IMAP_HOST, IMAP_PORT)
            imap.login(IMAP_USER, IMAP_PASS)

            imap.select("INBOX", readonly=True)
            status, data = imap.status("INBOX", "(MESSAGES UIDNEXT)")
            messages = 0
            uidnext = "1"

            if status == "OK" and data[0]:
                text = safe_decode(data[0])
                m = re.search(r'MESSAGES\s+(\d+)', text)
                if m:
                    messages = int(m.group(1))
                n = re.search(r'UIDNEXT\s+(\d+)', text)
                if n:
                    uidnext = n.group(1)

            inbox_changed = (
                len(latest_emails["inbox"]) != messages or
                (latest_emails["inbox"] and latest_emails["inbox"][0].get("uidnext") != uidnext)
            )

            if inbox_changed:
                imap.select('"INBOX"', readonly=False)
                current_emails = fetch_folder_emails(imap, "INBOX")

                old_uids = {e["uid"] for e in latest_emails["inbox"]}

                latest_emails["inbox"] = fetch_folder_emails(imap, "INBOX")
                new_mail_event.set()

                for email in current_emails:
                    if email["uid"] not in old_uids:
                        uid = email["uid"]

                        raw_from = email.get("from", "Unknown <unknown@example.com>")
                        # Example raw_from values:
                        #   "John Doe <john@example.com>"
                        #   "john@example.com"
                        #   "=?utf-8?q?John_Doe?= <john@example.com>"

                        match = re.search(r'([^<]+?)\s*<([^>]+)>', raw_from)
                        if match:
                            sender_name = match.group(1).strip().replace('"', '')
                            sender_email = match.group(2).strip()
                        else:
                            sender_email = raw_from.strip()
                            email_match = re.search(r'<([^>]+)>', raw_from)

                            if email_match:
                                sender_email = email_match.group(1)
                            sender_name = re.sub(r'=\?.*?\?=','', raw_from).strip()
                            if not sender_name or sender_name == sender_email:
                                sender_name = sender_email.split('@')[0].replace('.', ' ').title()

                        raw_to = email.get("to", "")                                   # ← same as "from"

                        match = re.search(r'([^<]+?)\s*<([^>]+)>', raw_to)
                        if match:
                            recipient_name = match.group(1).strip().replace('"', '')
                            recipient_email = match.group(2).strip()
                        else:
                            recipient_email = raw_to.strip()
                            email_match = re.search(r'<([^>]+)>', raw_to)
                            if email_match:
                                recipient_email = email_match.group(1)
                            recipient_name = re.sub(r'=\?.*?\?=','', raw_to).strip()
                            if not recipient_name or recipient_name == recipient_email:
                                recipient_name = recipient_email.split('@')[0].replace('.', ' ').title() if '@' in recipient_email else "Unknown"

                        subject = email.get("subject", "(no subject)")
                        body = email.get("body", "") or email.get("text", "") or email.get("html", "")
                        body_preview = (body or "(no body)").replace("\n", " ")

                        print("New email")
                        print(f"Sender Name     : {sender_name}")
                        print(f"Sender Email    : {sender_email}")
                        print(f"Recipient Name  : {recipient_name}")
                        print(f"Recipient Email : {recipient_email}")
                        print(f"Subject         : {subject}")
                        print(f"Body preview    : {body_preview}")
                        print(f"UID             : {uid}\n")

                        att_names = [att["name"] for att in email.get("attachments", [])]
                        emails_for_ai = []
                        emails_for_ai.append({
                            "sender_name": sender_name,
                            "sender_email": sender_email,
                            "recipient_name": recipient_name,
                            "recipient_email": recipient_email,
                            "subject": subject,
                            "body": body,
                            "attachment_filenames": att_names or None
                        })

                        verdicts = batch_predict(emails_for_ai)
                        verdict_dict = verdicts[0] if verdicts else {"verdict": "legit"}

                        print("\n" + "="*60)
                        print("PhishAI Response:")
                        print(verdict_dict)
                        print("="*60 + "\n")

                        is_phishing = verdict_dict.get("verdict", "legit").lower() == "phishing"

                        if is_phishing:
                            move_msg(imap, uid, "INBOX", "Phishing")
                            print(f" → MOVED TO PHISHING FOLDER")
                        else:
                            print(f" → Legitimate email — kept in Inbox")

                        # Refresh both folders
                        latest_emails["inbox"] = fetch_folder_emails(imap, "INBOX")
                        latest_emails["phishing"] = fetch_folder_emails(imap, "Phishing")
                        new_mail_event.set()

            # Refresh other folders only if count changed
            sent_folder = detect_sent_folder(imap)
            trash_folder = detect_trash_folder(imap)

            for folder_name, key in [
                (sent_folder, "sent"),
                (trash_folder, "trash"),
                ("Phishing", "phishing")
            ]:
                try:
                    imap.select(f'"{folder_name}"', readonly=True)
                    status, data = imap.search(None, "ALL")
                    count = len(data[0].split()) if status == "OK" and data[0] else 0
                    if len(latest_emails[key]) != count:
                        latest_emails[key] = fetch_folder_emails(imap, folder_name)
                        new_mail_event.set()
                except:
                    pass

            imap.logout()

        except Exception as e:
            print(f"IMAP poll error: {e}")
            if imap:
                try:
                    imap.logout()
                except:
                    pass

        time.sleep(5)

Thread(target=imap_polling_watcher, daemon=True).start()
