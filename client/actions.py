import imaplib

from email.utils import parsedate_to_datetime

from config import IMAP_HOST, IMAP_PORT, IMAP_USER, IMAP_PASS

from core.state import latest_emails, new_mail_event

from utils.helpers import detect_trash_folder
from utils.helpers import detect_sent_folder, detect_trash_folder


def move_msg(imap, msg_uid, src_folder, dst_folder):
    try:
        # Must be in the source folder and in read-write mode
        imap.select(f'"{src_folder}"', readonly=False)

        # Use UID commands — this is the key fix!
        status, _ = imap.uid('COPY', msg_uid, dst_folder)
        if status != 'OK':
            print(f"[MOVE FAILED] COPY failed for UID {msg_uid}")
            return False

        # Mark as Deleted using UID
        imap.uid('STORE', msg_uid, '+FLAGS', '\\Deleted')
        
        # Expunge using UID command (some servers require it)
        imap.expunge()
        
        print(f"[MOVE SUCCESS] UID {msg_uid} moved from {src_folder} → {dst_folder}")
        return True

    except Exception as e:
        print(f"[MOVE ERROR] {e}")
        return False


def move_or_delete_email(email_id, action="trash"):
    try:
        source_folder = None
        target_email = None
        folder_map = {
            "inbox": "INBOX",
            "sent": detect_sent_folder
        }

        for folder_key, folder_name in folder_map.items():
            for e in latest_emails[folder_key]:
                if e["id"] == email_id:
                    source_folder = folder_name() if callable(folder_name) else folder_name
                    target_email = e
                    break
            if target_email:
                break

        if not target_email or not source_folder:
            return False

        dest_folder = detect_trash_folder() if action == "trash" else "Archive"

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

        # Instant trash update (your genius fix)
        if action == "trash" and target_email:
            trash_copy = target_email.copy()
            trash_copy["read"] = True
            latest_emails["trash"].insert(0, trash_copy)
            latest_emails["trash"].sort(
                key=lambda e: parsedate_to_datetime(e["date"]).timestamp() if e["date"] else 0,
                reverse=True
            )

        # Remove from source
        for folder in ["inbox", "sent"]:
            latest_emails[folder] = [e for e in latest_emails[folder] if e["id"] != email_id]

        new_mail_event.set()
        return True
    except Exception as e:
        print(f"Move/Delete failed: {e}")
        return False
