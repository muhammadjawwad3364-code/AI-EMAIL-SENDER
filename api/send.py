"""
Vercel serverless function: sends one email per request over SMTP.

Settings come from Vercel Environment Variables:
  SMTP_USER   your email address (e.g. you@gmail.com)
  SMTP_PASS   Google App password (not your normal password)
  ACCESS_KEY  any secret phrase; the app asks for it so strangers can't use your site
  FROM_NAME   optional sender name, e.g. Javlopers
  REPLY_TO    optional reply-to address
  SMTP_HOST   optional, default smtp.gmail.com
  SMTP_PORT   optional, default 587
"""

import base64
import hmac
import json
import os
import re
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr, make_msgid
from http.server import BaseHTTPRequestHandler

EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def settings():
    return {
        "host": os.environ.get("SMTP_HOST", "smtp.gmail.com"),
        "port": int(os.environ.get("SMTP_PORT", "587") or 587),
        "user": os.environ.get("SMTP_USER", "").strip(),
        "password": os.environ.get("SMTP_PASS", "").replace(" ", ""),
        "from_name": os.environ.get("FROM_NAME", "").strip(),
        "reply_to": os.environ.get("REPLY_TO", "").strip(),
    }


def connect(c):
    ctx = ssl.create_default_context()
    if c["port"] == 465:
        server = smtplib.SMTP_SSL(c["host"], c["port"], context=ctx, timeout=25)
    else:
        server = smtplib.SMTP(c["host"], c["port"], timeout=25)
        server.starttls(context=ctx)
    server.login(c["user"], c["password"])
    return server


def build_message(c, to_addr, subject, body, attachments):
    msg = EmailMessage()
    msg["From"] = formataddr((c["from_name"], c["user"]))
    msg["To"] = to_addr
    msg["Subject"] = subject
    if c["reply_to"]:
        msg["Reply-To"] = c["reply_to"]
    msg["Message-ID"] = make_msgid(domain=c["user"].split("@")[-1])
    msg.set_content(body)
    for a in attachments or []:
        maintype, _, subtype = (a.get("type") or "application/octet-stream").partition("/")
        msg.add_attachment(base64.b64decode(a["data"]), maintype=maintype,
                           subtype=subtype or "octet-stream", filename=a.get("name") or "file")
    return msg


class handler(BaseHTTPRequestHandler):
    def _reply(self, code, data):
        body = json.dumps(data).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        self._reply(405, {"ok": False, "error": "Use POST."})

    def do_POST(self):
        key = os.environ.get("ACCESS_KEY", "")
        if not key:
            return self._reply(500, {"ok": False, "fatal": True,
                                     "error": "ACCESS_KEY is not set in your Vercel environment variables."})
        given = self.headers.get("x-access-key", "")
        if not hmac.compare_digest(key.encode("utf-8"), given.encode("utf-8")):
            return self._reply(401, {"ok": False, "fatal": True, "error": "Wrong access key."})

        c = settings()
        if not c["user"] or not c["password"]:
            return self._reply(500, {"ok": False, "fatal": True,
                                     "error": "SMTP_USER and SMTP_PASS must be set in your Vercel environment variables."})

        try:
            n = int(self.headers.get("Content-Length") or 0)
            p = json.loads(self.rfile.read(n) or b"{}")
        except Exception:
            return self._reply(400, {"ok": False, "error": "Bad request."})

        action = p.get("action", "send")
        if str(p.get("from_name", "")).strip():
            c["from_name"] = str(p["from_name"]).strip().replace("\r", "").replace("\n", "")
        try:
            if action == "verify":
                connect(c).quit()
                return self._reply(200, {"ok": True, "from": c["user"], "from_name": c["from_name"]})

            if action not in ("send", "test"):
                return self._reply(400, {"ok": False, "error": "Unknown action."})

            to_addr = c["user"] if action == "test" else str(p.get("to", "")).strip()
            if not EMAIL_RE.match(to_addr):
                return self._reply(400, {"ok": False, "error": f"Invalid email address: {to_addr}"})
            subject = str(p.get("subject", ""))
            if action == "test":
                subject = "[TEST] " + subject
            server = connect(c)
            server.send_message(build_message(c, to_addr, subject, str(p.get("body", "")),
                                              p.get("attachments")))
            server.quit()
            return self._reply(200, {"ok": True, "to": to_addr})

        except smtplib.SMTPAuthenticationError:
            return self._reply(200, {"ok": False, "fatal": True,
                                     "error": "Mail server rejected the login. Check SMTP_USER and the App password in SMTP_PASS."})
        except smtplib.SMTPRecipientsRefused as e:
            return self._reply(200, {"ok": False, "error": f"Address refused: {list(e.recipients)}"})
        except Exception as e:
            return self._reply(200, {"ok": False, "error": str(e) or e.__class__.__name__})
