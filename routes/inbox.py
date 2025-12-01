from flask import Blueprint, render_template, jsonify, request
from core.state import latest_emails

inbox_bp = Blueprint('inbox', __name__)

@inbox_bp.route("/")
def inbox():
    return render_template("index.html", emails=latest_emails["inbox"])

@inbox_bp.route("/api/emails")
def api_emails():
    folder = request.args.get("folder", "inbox").lower()

    if folder in ["sent", "sent mail", "[gmail]/sent mail", "sent items"]:
        return jsonify(latest_emails["sent"])
    if folder in ["trash", "bin", "deleted", "[gmail]/trash"]:
        return jsonify(latest_emails["trash"])
    if folder in ["phishing", "spam"]:
        return jsonify(latest_emails["phishing"])

    return jsonify(latest_emails["inbox"])
