from flask import Blueprint, request, jsonify
from threading import Thread

import time

from core.state import latest_emails, new_mail_event

from client.sender import send_email_logic
from client.actions import move_or_delete_email

actions_bp = Blueprint('actions', __name__)

@actions_bp.route("/send", methods=["POST"])
def send_email():
    return send_email_logic()

@actions_bp.route("/action", methods=["POST"])
def email_action():
    try:
        data = request.get_json()
        email_id = data.get("id")
        action = data.get("action")

        if not email_id or action not in ["trash", "archive"]:
            return jsonify({"error": "invalid"}), 400

        # Background real IMAP move + instant UI update
        Thread(target=move_or_delete_email, args=(email_id, action), daemon=True).start()

        # Instant UI removal from inbox/sent
        for folder in ["inbox", "sent"]:
            latest_emails[folder] = [e for e in latest_emails[folder] if e["id"] != email_id]
        
        new_mail_event.set()
        return jsonify({"status": "ok"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
