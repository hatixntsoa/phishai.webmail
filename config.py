# config.py
import os
from dotenv import load_dotenv

load_dotenv()

IMAP_HOST = os.getenv("IMAP_HOST", "localhost")
IMAP_PORT = int(os.getenv("IMAP_PORT", "143"))
IMAP_USER = os.getenv("IMAP_USER")
IMAP_PASS = os.getenv("IMAP_PASS")
SMTP_HOST = os.getenv("SMTP_HOST", "localhost")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
USE_TLS = os.getenv("SMTP_TLS", "true").lower() == "true"
