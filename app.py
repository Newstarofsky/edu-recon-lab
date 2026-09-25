"""
edu-recon-lab  —  Educational reconnaissance prototype
======================================================
A SINGLE Flask app that demonstrates the core mechanism behind three
well-known security tools, for a supervised lab on systems you own:

    * Seeker    -> browser Geolocation API capture      (/geo)
    * CamHacker -> getUserMedia webcam frame capture     (/cam)
    * Zphisher  -> credential-form capture               (/portal)

Everything captured is written locally (sqlite + ./captures) and shown
on /dashboard so you can inspect exactly what each technique leaks.

ETHICAL GUARDRAILS (intentional — an attacker would remove these):
    * Every capture page shows an unavoidable consent banner.
    * Binds to 127.0.0.1 by default. No tunnel is wired in.
    * The fake portal is a generic "ACME" brand, not a cloned real site.
    * The credential page ends on an explicit "this was a simulation" screen.

Run:  python app.py     then open http://127.0.0.1:5000
"""

import base64
import datetime as dt
import os
import sqlite3

from flask import (Flask, g, redirect, render_template, request,
                   send_from_directory, url_for)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "lab.db")
CAPTURE_DIR = os.path.join(BASE_DIR, "captures")
os.makedirs(CAPTURE_DIR, exist_ok=True)

app = Flask(__name__)


# --------------------------------------------------------------------------- #
#  Database helpers
# --------------------------------------------------------------------------- #
def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(_exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = sqlite3.connect(DB_PATH)
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS geo (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT, ip TEXT, ua TEXT,
            lat REAL, lon REAL, accuracy REAL,
            platform TEXT, screen TEXT, lang TEXT, cores TEXT
        );
        CREATE TABLE IF NOT EXISTS cam (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT, ip TEXT, ua TEXT, filename TEXT
        );
        CREATE TABLE IF NOT EXISTS creds (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT, ip TEXT, ua TEXT,
            username TEXT, password TEXT
        );
        """
    )
    db.commit()
    db.close()


def now():
    return dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# --------------------------------------------------------------------------- #
#  Landing + capture pages
# --------------------------------------------------------------------------- #
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/geo")
def geo_page():
    # Seeker essence: a lure page that requests the Geolocation permission.
    return render_template("geo.html")


@app.route("/cam")
def cam_page():
    # CamHacker essence: a lure page that requests camera permission.
    return render_template("cam.html")


@app.route("/portal")
def portal_page():
    # Zphisher essence: a generic fake login form (NOT a cloned real brand).
    return render_template("login.html")


@app.route("/caught")
def caught_page():
    return render_template("caught.html")


@app.route("/detect")
def detect_page():
    # Blue-team side: shows the user which permissions a page can request and
    # how to notice/deny them. Purely client-side awareness — captures nothing.
    return render_template("detect.html")


# --------------------------------------------------------------------------- #
#  Capture endpoints  (the "harvest" side)
# --------------------------------------------------------------------------- #
@app.route("/api/geo", methods=["POST"])
def api_geo():
    d = request.get_json(force=True, silent=True) or {}
    db = get_db()
    db.execute(
        "INSERT INTO geo (ts, ip, ua, lat, lon, accuracy, platform, screen, lang, cores)"
        " VALUES (?,?,?,?,?,?,?,?,?,?)",
        (now(), request.remote_addr, request.headers.get("User-Agent", ""),
         d.get("lat"), d.get("lon"), d.get("accuracy"),
         d.get("platform"), d.get("screen"), d.get("lang"), str(d.get("cores"))),
    )
    db.commit()
    return {"status": "ok"}


@app.route("/api/cam", methods=["POST"])
def api_cam():
    d = request.get_json(force=True, silent=True) or {}
    data_url = d.get("image", "")
    if "," not in data_url:
        return {"status": "no-image"}, 400
    # data URL looks like "data:image/png;base64,AAAA..." — strip the header.
    raw = base64.b64decode(data_url.split(",", 1)[1])
    fname = f"cam_{dt.datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.png"
    with open(os.path.join(CAPTURE_DIR, fname), "wb") as fh:
        fh.write(raw)
    db = get_db()
    db.execute(
        "INSERT INTO cam (ts, ip, ua, filename) VALUES (?,?,?,?)",
        (now(), request.remote_addr, request.headers.get("User-Agent", ""), fname),
    )
    db.commit()
    return {"status": "ok", "filename": fname}


@app.route("/api/portal", methods=["POST"])
def api_portal():
    # Demonstrates credential capture. Real value here is showing that a
    # look-alike form + a POST handler is all it takes — the lesson is
    # "check the URL / use 2FA", not the code itself.
    db = get_db()
    db.execute(
        "INSERT INTO creds (ts, ip, ua, username, password) VALUES (?,?,?,?,?)",
        (now(), request.remote_addr, request.headers.get("User-Agent", ""),
         request.form.get("username", ""), request.form.get("password", "")),
    )
    db.commit()
    return redirect(url_for("caught_page"))


# --------------------------------------------------------------------------- #
#  Operator dashboard
# --------------------------------------------------------------------------- #
@app.route("/dashboard")
def dashboard():
    db = get_db()
    geo = db.execute("SELECT * FROM geo ORDER BY id DESC").fetchall()
    cam = db.execute("SELECT * FROM cam ORDER BY id DESC").fetchall()
    creds = db.execute("SELECT * FROM creds ORDER BY id DESC").fetchall()
    return render_template("dashboard.html", geo=geo, cam=cam, creds=creds)


@app.route("/captures/<path:fname>")
def captures(fname):
    return send_from_directory(CAPTURE_DIR, fname)


if __name__ == "__main__":
    init_db()
    # Host/port are configurable for lab use.
    #   Default 127.0.0.1  -> reachable only from this machine.
    #   Set LAB_HOST=0.0.0.0 to expose on the LAN so you can test from OTHER
    #   VMs you own in your isolated lab network (attacker-VM -> victim-VM).
    #   Only do this on a private lab segment with machines you control.
    host = os.environ.get("LAB_HOST", "127.0.0.1")
    port = int(os.environ.get("LAB_PORT", "5000"))
    if host != "127.0.0.1":
        print(f"[!] Binding to {host}:{port} — LAN-exposed. Use only inside "
              f"your own isolated lab with consenting/owned machines.")
    app.run(host=host, port=port, debug=True)
