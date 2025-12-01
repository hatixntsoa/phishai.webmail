from config import IMAP_HOST, IMAP_PORT, IMAP_USER, IMAP_PASS
import imaplib

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
