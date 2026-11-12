"""
Vercel serverless function for "Continue with Google".

GET  /api/google                         -> which sign-in options are configured
POST /api/google {action: "exchange", code}           -> tokens after sign-in
POST /api/google {action: "refresh", refresh_token}   -> a fresh access token

Environment variables (Vercel > Settings > Environment Variables):
  GOOGLE_CLIENT_ID      OAuth client ID (Web application) from Google Cloud
  GOOGLE_CLIENT_SECRET  its client secret
"""

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler

TOKEN_URL = "https://oauth2.googleapis.com/token"


def post_token(data):
    req = urllib.request.Request(
        TOKEN_URL, data=urllib.parse.urlencode(data).encode("utf-8"),
        headers={"Content-Type": "application/x-www-form-urlencoded"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        try:
            return json.loads(e.read())
        except Exception:
            return {"error": f"HTTP {e.code}"}
    except Exception as e:
        return {"error": str(e)}


def token_reply(res):
    if "access_token" in res:
        out = {"ok": True, "access_token": res["access_token"],
               "expires_in": int(res.get("expires_in", 3600)), "scope": res.get("scope", "")}
        if res.get("refresh_token"):
            out["refresh_token"] = res["refresh_token"]
        return out
    return {"ok": False, "error": res.get("error_description") or res.get("error") or "Google sign-in failed."}


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
        self._reply(200, {
            "client_id": os.environ.get("GOOGLE_CLIENT_ID", "").strip(),
            "smtp": bool(os.environ.get("SMTP_USER") and os.environ.get("SMTP_PASS") and os.environ.get("ACCESS_KEY")),
        })

    def do_POST(self):
        # Basic CSRF protection: our page sets this header, and requests must come from this site.
        if self.headers.get("X-Requested-With") != "XmlHttpRequest":
            return self._reply(403, {"ok": False, "error": "Forbidden."})
        origin = self.headers.get("Origin", "")
        host = self.headers.get("X-Forwarded-Host") or self.headers.get("Host", "")
        if origin and urllib.parse.urlparse(origin).netloc != host:
            return self._reply(403, {"ok": False, "error": "Forbidden origin."})

        cid = os.environ.get("GOOGLE_CLIENT_ID", "").strip()
        secret = os.environ.get("GOOGLE_CLIENT_SECRET", "").strip()
        if not cid or not secret:
            return self._reply(500, {"ok": False, "error": "GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET must be set in Vercel."})

        try:
            n = int(self.headers.get("Content-Length") or 0)
            p = json.loads(self.rfile.read(n) or b"{}")
        except Exception:
            return self._reply(400, {"ok": False, "error": "Bad request."})

        action = p.get("action")
        if action == "exchange":
            code = str(p.get("code", ""))
            # Google's popup flow uses the page origin as redirect_uri; older setups use "postmessage".
            candidates = [c for c in (origin, "postmessage") if c]
            res = {}
            for redirect in candidates:
                res = post_token({"code": code, "client_id": cid, "client_secret": secret,
                                  "redirect_uri": redirect, "grant_type": "authorization_code"})
                if "access_token" in res or res.get("error") != "redirect_uri_mismatch":
                    break
            return self._reply(200, token_reply(res))

        if action == "refresh":
            res = post_token({"refresh_token": str(p.get("refresh_token", "")), "client_id": cid,
                              "client_secret": secret, "grant_type": "refresh_token"})
            return self._reply(200, token_reply(res))

        return self._reply(400, {"ok": False, "error": "Unknown action."})
