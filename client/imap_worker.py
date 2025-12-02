from threading import Thread
import imaplib
import time

from core.state import latest_emails, new_mail_event
from client.parser import parse_email, get_timestamp
from utils.helpers import detect_sent_folder, detect_trash_folder
from config import IMAP_HOST, IMAP_PORT, IMAP_USER, IMAP_PASS

def safe_decode(x):
    if isinstance(x, bytes):
        return x.decode('utf-8', errors='ignore')
    return str(x)

def fetch_folder_emails(imap, folder=None):
    if folder:
        imap.select(folder)
    status, data = imap.uid('SEARCH', None, "ALL")
    if status != "OK" or not data[0]:
        return []
    email_ids = data[0].split()[-200:]
    emails = []
    for num in email_ids:
        try:
            status, msg_data = imap.uid('FETCH', num, "(RFC822 FLAGS)")
            if msg_data == [None]:
                continue
            raw = msg_data[0][1]
            parsed = parse_email(raw)
            parsed["uid"] = safe_decode(num)
            emails.append(parsed)
        except:
            continue
    emails.sort(key=get_timestamp, reverse=True)
    return emails

print("Running initial IMAP sync...")
imap = imaplib.IMAP4(IMAP_HOST, IMAP_PORT)
imap.login(IMAP_USER, IMAP_PASS)
latest_emails["inbox"] = fetch_folder_emails(imap, "INBOX")
latest_emails["sent"] = fetch_folder_emails(imap, detect_sent_folder(imap))
latest_emails["trash"] = fetch_folder_emails(imap, detect_trash_folder(imap))
try:
    latest_emails["phishing"] = fetch_folder_emails(imap, "Phishing")
except:
    latest_emails["phishing"] = []
imap.logout()
new_mail_event.set()
print("Initial sync complete — inbox ready!")

# BACKGROUND POLLING — ONLY PUSH WHEN REAL CHANGE
def imap_polling_watcher():
    while True:
        try:
            imap = imaplib.IMAP4(IMAP_HOST, IMAP_PORT)
            imap.login(IMAP_USER, IMAP_PASS)

            # INBOX: fast detection using message count + latest UID
            imap.select("INBOX")
            status, count_data = imap.status("INBOX", "(MESSAGES)")
            current_count = 0
            if status == "OK" and count_data[0]:
                count_str = safe_decode(count_data[0]).split()
                current_count = int(count_str[2][:-1]) if len(count_str) > 2 else 0

            status, data = imap.search(None, "ALL")
            latest_uid = "0"
            if status == "OK" and data[0]:
                uids = data[0].split()
                latest_uid = safe_decode(uids[-1]) if uids else "0"

            inbox_changed = (
                not latest_emails["inbox"] or
                len(latest_emails["inbox"]) != current_count or
                latest_emails["inbox"][0].get("uid", "0") != latest_uid
            )

            if inbox_changed:
                latest_emails["inbox"] = fetch_folder_emails(imap, "INBOX")
                new_mail_event.set()
                # print("New email detected → pushing update")

            # SENT, TRASH, PHISHING — only if count changed
            for folder_name, key in [
                (detect_sent_folder(imap), "sent"),
                (detect_trash_folder(imap), "trash")
            ]:
                imap.select(folder_name)
                status, data = imap.search(None, "ALL")
                msg_count = len(data[0].split()) if status == "OK" and data[0] else 0
                if len(latest_emails[key]) != msg_count:
                    latest_emails[key] = fetch_folder_emails(imap, folder_name)
                    new_mail_event.set()

            # Phishing folder
            try:
                imap.select("Phishing")
                status, data = imap.search(None, "ALL")
                msg_count = len(data[0].split()) if status == "OK" and data[0] else 0
                if len(latest_emails["phishing"]) != msg_count:
                    latest_emails["phishing"] = fetch_folder_emails(imap, "Phishing")
                    new_mail_event.set()
            except:
                pass

            imap.logout()

        except Exception as e:
            print(f"IMAP poll error: {e}")

        time.sleep(5)

Thread(target=imap_polling_watcher, daemon=True).start()
