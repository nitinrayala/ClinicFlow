"""Read-oriented deployed checks; creates and revokes test login sessions only."""

import argparse
import http.cookiejar
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True)
    args = parser.parse_args()
    base = args.base_url.rstrip("/")
    parsed = urllib.parse.urlsplit(base)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.path:
        parser.error("Use an origin such as https://your-app.onrender.com")
    if parsed.scheme != "https" and parsed.hostname not in {"localhost", "127.0.0.1"}:
        parser.error("Remote smoke checks require HTTPS")
    password = os.environ.get("DEMO_PASSWORD")
    if not password:
        parser.error("Set DEMO_PASSWORD in your shell; do not pass it as a command argument")
    cookies = http.cookiejar.CookieJar()
    client = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookies))

    def request(path, method="GET", payload=None, expected=200):
        data = json.dumps(payload).encode() if payload is not None else None
        headers = {"Origin": base, "Accept": "application/json"}
        if data is not None:
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(base + "/api" + path, data=data, method=method, headers=headers)
        try:
            with client.open(req, timeout=15) as response:
                status, body = response.status, response.read()
        except urllib.error.HTTPError as error:
            status, body = error.code, error.read()
        if status != expected:
            raise RuntimeError(f"{method} {path}: expected {expected}, got {status}")
        print(f"PASS {method} {path} -> {status}")
        return json.loads(body) if body else None

    health = request("/health")
    if health.get("status") != "ok" or health.get("database") != "ok":
        raise RuntimeError("Health did not confirm database connectivity")
    request("/appointments", expected=401)
    for email, role in (("doctor@clinicflow.demo", "doctor"), ("staff@clinicflow.demo", "staff")):
        logged_in = False
        try:
            user = request("/auth/login", "POST", {"email": email, "password": password})
            logged_in = True
            if user.get("role") != role:
                raise RuntimeError("Login returned an unexpected role")
            if parsed.scheme == "https" and not any(cookie.secure for cookie in cookies):
                raise RuntimeError("HTTPS login did not set a Secure session cookie")
            request("/auth/me")
            request("/appointments", expected=200 if role == "doctor" else 403)
            request("/tasks")
        finally:
            if logged_in:
                request("/auth/logout", "POST", {})
        request("/auth/me", expected=401)
    print("Smoke passed. Run the browser workflow to verify approval and task completion.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (RuntimeError, urllib.error.URLError, TimeoutError, ValueError) as error:
        # Do not echo response bodies, connection URLs, cookies, or passwords.
        print(f"Smoke failed: {type(error).__name__}: {error}", file=sys.stderr)
        sys.exit(1)

