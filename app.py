import html
import hmac
import os
import secrets
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, abort, jsonify, request, send_from_directory

BASE = Path(__file__).resolve().parent
UPLOAD_DIR = Path(os.environ.get("UPLOAD_DIR", str(BASE / "uploads")))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
MAX_BYTES = 8 * 1024 * 1024
ALLOWED = {
    "image/jpeg": (".jpg", lambda b: b.startswith(b"\xff\xd8\xff")),
    "image/png": (".png", lambda b: b.startswith(b"\x89PNG\r\n\x1a\n")),
    "image/webp": (".webp", lambda b: len(b) >= 12 and b[:4] == b"RIFF" and b[8:12] == b"WEBP"),
}

app = Flask(__name__, static_folder=None)
app.config["MAX_CONTENT_LENGTH"] = MAX_BYTES


def admin_ok():
    auth = request.authorization
    username = os.environ.get("ADMIN_USER", "")
    password = os.environ.get("ADMIN_PASSWORD", "")
    if not username or not password or not auth:
        return False
    return hmac.compare_digest(auth.username or "", username) and hmac.compare_digest(auth.password or "", password)


def require_admin():
    if not os.environ.get("ADMIN_USER") or not os.environ.get("ADMIN_PASSWORD"):
        abort(503, "Set ADMIN_USER and ADMIN_PASSWORD in Render environment variables.")
    if not admin_ok():
        return ("Admin sign-in required", 401, {"WWW-Authenticate": 'Basic realm="Albert photo inbox"'})
    return None


@app.get("/")
def home():
    return send_from_directory(BASE, "index.html")


@app.get("/party-song.mp3")
def song():
    return send_from_directory(BASE, "party-song.mp3")


@app.get("/health")
def health():
    return jsonify(ok=True)


@app.post("/api/upload")
def upload():
    photo = request.files.get("photo")
    if request.form.get("consent") != "yes":
        return jsonify(error="Photo consent is required."), 400
    if photo is None or not photo.filename:
        return jsonify(error="Choose a photo first."), 400
    spec = ALLOWED.get(photo.mimetype)
    if spec is None:
        return jsonify(error="Use a JPEG, PNG, or WebP image."), 415
    extension, validator = spec
    header = photo.stream.read(16)
    photo.stream.seek(0)
    if not validator(header):
        return jsonify(error="The selected file is not a valid supported image."), 415
    name = secrets.token_urlsafe(18).replace("-", "a").replace("_", "b") + extension
    photo.save(UPLOAD_DIR / name)
    return jsonify(ok=True, message="Photo sent to Albert.")


@app.get("/admin")
def inbox():
    denied = require_admin()
    if denied:
        return denied
    files = sorted((p for p in UPLOAD_DIR.iterdir() if p.is_file() and p.suffix.lower() in {".jpg", ".png", ".webp"}), key=lambda p: p.stat().st_mtime, reverse=True)
    cards = []
    for path in files:
        stamp = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        safe = html.escape(path.name)
        cards.append(f'<article><a href="/admin/photos/{safe}"><img src="/admin/photos/{safe}" alt="Uploaded photo"></a><p>{stamp}</p></article>')
    body = "".join(cards) or "<p>No photos have been sent yet.</p>"
    return f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Photo inbox</title><style>body{{font:16px system-ui;background:#11131d;color:#f8f7fb;padding:24px}}main{{max-width:1000px;margin:auto}}section{{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:16px}}article{{padding:12px;background:#1a1e2b;border-radius:12px}}img{{width:100%;height:220px;object-fit:contain;background:#0b0d13;border-radius:8px}}p{{color:#b5b9c9;font-size:12px}}</style><main><h1>Photo inbox</h1><p>Only photos voluntarily submitted from the greeting page appear here.</p><section>{body}</section></main></html>'''


@app.get("/admin/photos/<path:name>")
def admin_photo(name):
    denied = require_admin()
    if denied:
        return denied
    if Path(name).name != name:
        abort(404)
    return send_from_directory(UPLOAD_DIR, name, max_age=0)


@app.errorhandler(413)
def too_large(_error):
    return jsonify(error="Image is too large. Maximum size is 8 MB."), 413
