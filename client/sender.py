from email.message import EmailMessage

from flask import request

import smtplib
import imaplib

import time

from config import IMAP_USER, IMAP_PASS, IMAP_HOST, IMAP_PORT, SMTP_HOST, SMTP_PORT, USE_TLS
from core.state import latest_emails, new_mail_event
from utils.helpers import detect_sent_folder

def send_email_logic():
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
            # smtp.starttls()
        else:
            smtp = smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT)
        smtp.login(IMAP_USER, IMAP_PASS)
        smtp.send_message(msg)
        smtp.quit()

        # Append to Sent folder via IMAP
        imap = imaplib.IMAP4(IMAP_HOST, IMAP_PORT)
        imap.login(IMAP_USER, IMAP_PASS)
        sent_folder = detect_sent_folder(imap) or "Sent"
        imap.append(sent_folder, None, imaplib.Time2Internaldate(time.time()), msg.as_bytes())
        imap.logout()

        # Add to local state instantly
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
