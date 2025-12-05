from email.utils import parsedate_to_datetime, getaddresses
from email.policy import default

import email
import time
import re

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

    sender_name = sender.split("<")[0].strip()
    if not sender_name:
        match = re.search(r'[\w\.-]+@[\w\.-]+', sender)
        sender_name = match.group(0) if match else sender

    # Parse the first recipient from the To header (name and email)
    to_header = msg.get("To") or ""
    recipient_name = ""
    recipient_email = ""
    if to_header:
        addrs = getaddresses([to_header])
        if addrs:
            name, addr = addrs[0]
            recipient_name = name.strip() or (addr or "")
            recipient_email = addr or ""

    return {
        "id": str(int(time.time() * 1000)) + str(hash(subject + body) % 1000),
        "sender": sender_name,
        "to": to_header,
        "recipient_name": recipient_name,
        "recipient_email": recipient_email,
        "subject": subject,
        "body": body,
        "date": date,
        "read": False,
        "from": msg["From"] or "Unknown <unknown@example.com>",
    }

def get_timestamp(email_obj):
    date_str = email_obj.get("date", "")
    if not date_str:
        return 0
    try:
        dt = parsedate_to_datetime(date_str)
        return dt.timestamp() if dt else 0
    except:
        return 0
