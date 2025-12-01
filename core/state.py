from threading import Event

latest_emails = {
    "inbox": [],
    "sent": [],
    "trash": [],
    "phishing": []
}
new_mail_event = Event()
